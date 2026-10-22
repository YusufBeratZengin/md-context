# Security policy

Version 0.1.x receives security fixes on a best-effort basis.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting for
[YusufBeratZengin/md-context](https://github.com/YusufBeratZengin/md-context/security/advisories/new)
when available. If it is unavailable, open an issue asking for a private reporting
channel, without exploit details or sensitive data. Include only synthetic
reproductions. Do not publish real notes, credentials, or generated caches.

## Data handling

md-context does not make network requests or execute note content. It reads local
UTF-8 Markdown and writes an index under `.md-context/` in the selected folder.
That index includes full text of every included note. Protect it like the source
folder and exclude it from version control and inappropriate backups.

`visibility: private` and `.mdcontextignore` prevent inclusion in new snapshots
and packs. CLI query and stats refresh before producing output. An unsuccessful
refresh emits no pack but can leave an older snapshot on disk. API callers must
rebuild snapshots themselves. References to excluded notes in public note bodies
are not redacted. Existing exports and backups are not deleted.

Symlink notes/directories are skipped; symlink cache paths and ignore files are
rejected. This is not a sandbox against concurrent filesystem changes or hostile
users who can alter the vault during a scan. Ignore rules are not access controls.

Treat retrieved content as untrusted input to an agent. Notes can contain prompt
injection, Markdown links, or incomplete code blocks after truncation. Review
packs before giving them to agents with tools. Any downstream command or service
you pipe into is responsible for its own data handling. Token estimates do not
guarantee a particular model's real token count.
