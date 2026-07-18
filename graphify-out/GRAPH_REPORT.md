# Graph Report - Toman_Interview_Task  (2026-07-18)

## Corpus Check
- 41 files · ~4,895 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 190 nodes · 291 edges · 39 communities (19 shown, 20 thin omitted)
- Extraction: 60% EXTRACTED · 40% INFERRED · 0% AMBIGUOUS · INFERRED: 116 edges (avg confidence: 0.59)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `037e24c1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Wallet API Layer|Wallet API Layer]]
- [[_COMMUNITY_Wallet Service Flow|Wallet Service Flow]]
- [[_COMMUNITY_Third Party Service|Third Party Service]]
- [[_COMMUNITY_Flask Request Handler|Flask Request Handler]]
- [[_COMMUNITY_Django Management|Django Management]]
- [[_COMMUNITY_Wallet App Configuration|Wallet App Configuration]]
- [[_COMMUNITY_WSGI Entry Point|WSGI Entry Point]]
- [[_COMMUNITY_Wallet URL Routing|Wallet URL Routing]]
- [[_COMMUNITY_Django Settings|Django Settings]]
- [[_COMMUNITY_ASGI Entry Point|ASGI Entry Point]]
- [[_COMMUNITY_Third Party Client|Third Party Client]]
- [[_COMMUNITY_Wallet Models|Wallet Models]]
- [[_COMMUNITY_Database Migration|Database Migration]]
- [[_COMMUNITY_Shared HTTP Client|Shared HTTP Client]]
- [[_COMMUNITY_Package Initialization|Package Initialization]]
- [[_COMMUNITY_Project Package|Project Package]]
- [[_COMMUNITY_Django Admin|Django Admin]]
- [[_COMMUNITY_Flask Async Dependency|Flask Async Dependency]]
- [[_COMMUNITY_Werkzeug Dependency|Werkzeug Dependency]]
- [[_COMMUNITY_Django Dependency|Django Dependency]]
- [[_COMMUNITY_Django REST Framework|Django REST Framework]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]

## God Nodes (most connected - your core abstractions)
1. `Withdrawal` - 21 edges
2. `Wallet` - 18 edges
3. `WithdrawalExecutionTests` - 17 edges
4. `FakeBankClient` - 15 edges
5. `WalletApiTests` - 15 edges
6. `BankResult` - 14 edges
7. `execute_withdrawal()` - 13 edges
8. `Transaction` - 12 edges
9. `Wallet Service` - 12 edges
10. `WithdrawalDispatcherTests` - 11 edges

## Surprising Connections (you probably didn't know these)
- `Requests` --semantically_similar_to--> `Requests`  [INFERRED] [semantically similar]
  third-party/requirements.txt → wallet/requirements.txt
- `Wallet Service` --conceptually_related_to--> `Wallet Service`  [INFERRED]
  docker-compose.yml → wallet/readme.md
- `process_withdrawal()` --calls--> `execute_withdrawal()`  [INFERRED]
  wallet/wallets/tasks.py → wallet/wallets/services/withdrawals.py
- `Third Party Service` --conceptually_related_to--> `Third Party App`  [INFERRED]
  docker-compose.yml → third-party/readme.md
- `Third Party Request` --conceptually_related_to--> `Third Party Service`  [INFERRED]
  wallet/readme.md → docker-compose.yml

## Hyperedges (group relationships)
- **Containerized Service Architecture** — docker_compose_wallet_service, docker_compose_third_party_service, wallet_readme_third_party_request [INFERRED 0.85]

## Communities (39 total, 20 thin omitted)

### Community 0 - "Wallet API Layer"
Cohesion: 0.22
Nodes (20): APIView, CreateAPIView, RetrieveAPIView, ApiIdempotency, Transaction, Wallet, Withdrawal, DepositSerializer (+12 more)

### Community 1 - "Wallet Service Flow"
Cohesion: 0.2
Nodes (8): BankResult, Small adapter around the provided third-party bank HTTP contract., RequestsBankClient, execute_withdrawal(), Reserve, call the bank without locks, then settle the reservation., FakeBankClient, SequenceBankClient, WithdrawalExecutionTests

### Community 2 - "Third Party Service"
Cohesion: 0.09
Nodes (21): Third Party Runtime, Third Party Service, Wallet Runtime, Wallet Service, App Entrypoint, Requirements File, Third Party App, API (+13 more)

### Community 3 - "Flask Request Handler"
Cohesion: 0.14
Nodes (6): TestCase, test_celery_task_invokes_application_service(), test_dispatcher_respects_batch_size(), test_stale_queued_withdrawal_is_recovered(), WalletApiTests, WithdrawalDispatcherTests

### Community 4 - "Django Management"
Cohesion: 0.17
Nodes (11): API flow, Automatic withdrawal flow, Big picture, code:mermaid (flowchart LR), code:mermaid (stateDiagram-v2), code:bash (docker compose up --build), Core data model, Operations (+3 more)

### Community 5 - "Wallet App Configuration"
Cohesion: 0.22
Nodes (7): dispatch_due_withdrawals(), publish_outbox_events(), Durable dispatcher: database state is authoritative, Celery is delivery., Claim at most one batch and publish tasks after the claim commits., recover_stale_queued_withdrawals(), process_withdrawal(), publish_outbox()

### Community 6 - "WSGI Entry Point"
Cohesion: 0.25
Nodes (4): Exception, deposit(), WalletServiceError, schedule_withdrawal()

### Community 7 - "Wallet URL Routing"
Cohesion: 0.29
Nodes (5): BankTransferAttempt, Meta, OutboxEvent, Status, Type

### Community 8 - "Django Settings"
Cohesion: 0.29
Nodes (3): BaseCommand, Command, Command

## Knowledge Gaps
- **48 isolated node(s):** `Run administrative tasks.`, `WSGI config for wallet project.  It exposes the WSGI callable as a module-level`, `wallet URL Configuration  The `urlpatterns` list routes URLs to views. For more`, `Django settings for wallet project.  Generated by 'django-admin startproject' us`, `ASGI config for wallet project.  It exposes the ASGI callable as a module-level` (+43 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Withdrawal` connect `Wallet API Layer` to `Django Settings`, `Wallet Service Flow`, `Flask Request Handler`, `Wallet URL Routing`?**
  _High betweenness centrality (0.083) - this node is a cross-community bridge._
- **Why does `WalletApiTests` connect `Flask Request Handler` to `Wallet API Layer`, `Wallet Service Flow`, `Wallet URL Routing`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `execute_withdrawal()` connect `Wallet Service Flow` to `Django Settings`, `Wallet App Configuration`, `WSGI Entry Point`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `Withdrawal` (e.g. with `FakeBankClient` and `SequenceBankClient`) actually correct?**
  _`Withdrawal` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `Wallet` (e.g. with `FakeBankClient` and `SequenceBankClient`) actually correct?**
  _`Wallet` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `WithdrawalExecutionTests` (e.g. with `BankResult` and `OutboxEvent`) actually correct?**
  _`WithdrawalExecutionTests` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `FakeBankClient` (e.g. with `BankResult` and `OutboxEvent`) actually correct?**
  _`FakeBankClient` has 5 INFERRED edges - model-reasoned connections that need verification._