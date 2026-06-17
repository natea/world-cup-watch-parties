# social-and-analytics Specification

## Purpose
TBD - created by archiving change add-social-and-analytics. Update Purpose after archive.
## Requirements
### Requirement: Link-unfurl metadata

The system SHALL serve Open Graph and Twitter Card metadata, plus a descriptive title and description, so that links to the site unfurl with a title, description, and image on major platforms.

#### Scenario: Page exposes share metadata

- **WHEN** the home page HTML is fetched
- **THEN** it includes a descriptive `<title>` and meta description, Open Graph tags (title, description, type, url, site name, and image), and Twitter Card tags using the large-image card type

#### Scenario: Image reference is absolute

- **WHEN** a crawler reads the `og:image`/`twitter:image` value
- **THEN** it is an absolute URL to the social card image, accompanied by its width, height, and alt text

### Requirement: Branded social card image

The system SHALL serve a 1200×630 social card image at the advertised URL.

#### Scenario: Card image is reachable and correctly sized

- **WHEN** the social card URL is requested
- **THEN** it returns a PNG image that is 1200×630

### Requirement: On-brand favicon and touch icon

The system SHALL provide a soccer-ball favicon and an Apple touch icon.

#### Scenario: Icons are linked and served

- **WHEN** the home page HTML is fetched
- **THEN** it links an SVG favicon and an Apple touch icon, and both assets are served by the site

### Requirement: Reproducible asset generation

The system SHALL provide a script that regenerates the favicon and social card from source.

#### Scenario: Regenerate brand assets

- **WHEN** the asset-generation script is run
- **THEN** it writes the favicon, the social card PNG, and the touch icon into the frontend public directory

### Requirement: Opt-in, privacy-first analytics

The system SHALL load cookieless visitor analytics only when an analytics website identifier is configured at build time, and SHALL load nothing otherwise.

#### Scenario: Analytics loads when configured

- **WHEN** the site is built with the analytics website identifier set
- **THEN** the built site loads the analytics script tagged with that identifier

#### Scenario: No analytics without configuration

- **WHEN** the site is built without the analytics website identifier
- **THEN** the built site loads no analytics script and sends no analytics traffic

#### Scenario: No consent banner required

- **WHEN** analytics is enabled
- **THEN** it is cookieless and requires no cookie-consent prompt

