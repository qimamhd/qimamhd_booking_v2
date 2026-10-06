# Production Cutover Runbook
Staging: backup DB+filestore, restore production clone, update custom_branch_13 and this module, run release_gate.py, complete UAT sheet, run event/stay concurrency and finance matrices, real API auth tests, migration dry-run+reconciliation.
Deployment: maintenance window, final backup, deploy exact RC, restart, upgrade only this module, inspect logs, smoke-test one event branch and one hotel branch plus API bootstrap/availability.
Rollback: restore code + DB + filestore together.
