# CRUD operations

| Resource | Create | Read | Update | Delete |
|---|---|---|---|---|
| Accounts | Admin creates Participant/Researcher; public signup creates Participant | Admin Users / own profile | Admin changes name, username, role or resets password | Admin deletes non-owner accounts after typing username |
| Lessons | Admin Content, complete English and Bangla | Learning Academy / Admin Content | Bilingual text and quizzes; quiz changes reset completion | Archive and restore; historical attempts remain |
| Video library | Admin uploads and labels a video | Library, games, research | Metadata, difficulty and independently verified label | Archive and restore; historical media references remain |
| Scans | Actual upload, supported public link or companion | Private history; Admin Records metadata | Scan/source title | Remove original, cached playback and result; quota policy retained |
| Support | Member support form | Member support / Admin Operations / Records | Reply, resolve, or correct record text | Admin Records with ID confirmation |
| Subscriptions | Member Premium request and transaction ID | Plans / Operations / Records | Pending request metadata; approval uses payment verification | Admin deletes request records with ID confirmation; active membership unaffected |
| Research | Qualified user submits an independent judgment; model computes result | Research dashboard / Admin Records | Admin review note only | Admin removes evaluation and associated learning sample with ID confirmation |

Predictions, original research answers, game points and audit/payment-proof records are not arbitrary editable fields. Their creation comes from the real workflow. Account deletion preserves a minimal hashed approved-transaction fingerprint to prevent transaction reuse; it does not keep a deleted account logged in.

There are three roles: Admin, Researcher and Participant. Admin is a singleton owner protected by API validation and a unique database index. Moderator has been retired. Every admin write is permission-checked and audited. Foreign keys are enabled for SQLite; account deletion handles dependent rows transactionally and removes media only after database commit. Deletion is blocked during active scanning or a live game.
