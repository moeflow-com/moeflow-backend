# models

Persistent models in MongoDB.

## Core


### Global

- `Language`
- `VCode`
- `Captcha`
- `SiteSetting`

### User

- `User`
- `Message`

### Team

- `Team`
- `TeamPermission`
- `TeamUserRelation`
- `TeamRole`
- `Application`
- `ApplicationStatus`
- `Invitation`
- `InvitationStatus`

### Unused? Terms

- `TermBank`
- `TermGroup`
- `Term`

### Project level

- `Project`
    - `Target[]`
    - `File[]`
- `ProjectSet`
- `ProjectRole`
- `ProjectUserRelation`
- `ProjectAllowApplyType`
- `ProjectPermission`
- `Output`

### Inside project

- `File`
    - `FileTargetCache`
- `Source`: `(rank, x, y, content)`
- `Translation`: `(User, Source, Target) -> (content, proof_content)`
- `Tip`: `(User, Source, Target) -> (content)`
