from dataclasses import dataclass
from typing import Literal
import io
import click
from app.models.file import File
from app.models.team import Team
from app.models.project import ProjectSet, Project
import csv
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SizeEntry:
    team_id: str
    team_name: str
    project_set_id: str
    project_set_name: str
    project_id: str
    project_name: str
    num_files: int
    total_size_kb: int


@click.command("fsck")
@click.option("--export-csv", type=click.File("w"), help="export statistics to csv")
@click.option(
    "--sum-by",
    type=click.Choice(["team", "project_set", "project"]),
    default="team",
    help="export statistics to csv",
)
def fsck(
    *, export_csv: io.FileIO | None, sum_by: Literal["team", "project_set", "project"]
):
    logger.info("Running fsck")
    size_entries: list[SizeEntry] = [
        _sum_by_project(t, ps, p)
        for t in Team.objects()
        for ps in ProjectSet.objects(team=t)
        for p in Project.objects(project_set=ps)
    ]
    if export_csv:
        writer = csv.DictWriter(export_csv, fieldnames=SizeEntry.__dataclass_fields__)
        writer.writeheader()
        for entry in size_entries:
            writer.writerow(entry.__dict__)
        export_csv.close()
    else:
        for entry in size_entries:
            logger.info(entry)


def _sum_by_project(t: Team, ps: ProjectSet, p: Project) -> SizeEntry:
    files = File.objects(project=p)
    num_files = len(files)
    size_kb = sum(f.file_size for f in files)
    return SizeEntry(
        team_id=t.id,
        team_name=t.name,
        project_set_id=ps.id,
        project_set_name=ps.name,
        project_id=p.id,
        project_name=p.name,
        total_size_kb=size_kb,
        num_files=num_files,
    )
