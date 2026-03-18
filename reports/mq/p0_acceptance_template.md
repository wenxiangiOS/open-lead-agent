# P0 Acceptance Report Template

- Date:
- Commit:
- Executor (model/human):
- Environment:

## Scope

- [ ] ingest API
- [ ] atomic enqueue
- [ ] user lock
- [ ] worker turn processing
- [ ] generation stale drop
- [ ] outbox write + sender retry
- [ ] backpressure

## Test Commands

```bash
# add exact commands
```

## Results Summary

- Case 1 (multi-message during running):
- Case 2 (cancel during running, stale drop):
- Case 3 (dedupe):
- Case 4 (worker restart recovery):
- Case 5 (sender retry):
- Case 6 (queue_full backpressure):

## Metrics / Logs Evidence

- pending_depth:
- stale_drop_count:
- sender_success_rate:
- queue_full_reject_count:

## Risks / Open Items

1.
2.

## Verdict

- [ ] PASS (P0 can be marked DONE)
- [ ] FAIL (keep P0 as NOT_DONE)
