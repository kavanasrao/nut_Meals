# API Reference

Base path: `/api/v1` (see `app/config.py::API_V1_PREFIX`).
All endpoints (except `/health`, `/health/ready`) require a `Bearer` JWT
issued by the central Auth service, verified locally against
`JWT_SECRET_KEY` / `JWT_AUDIENCE`.

The full, always-up-to-date, machine-readable spec is served at
`/api/v1/openapi.json` and rendered at `/api/v1/docs`. This document is a
human-oriented summary.

## Auth & RBAC

Every route depends on one of these role gates (`app/core/rbac.py`):

| Dependency | Roles allowed | Used by |
|---|---|---|
| `require_read` | `procurement_admin`, `procurement_officer`, `finance_viewer`, `auditor` | all `GET` routes |
| `require_write` | `procurement_admin`, `procurement_officer` | create/update routes |
| `require_approver` | `procurement_admin` | `POST /purchase-orders/{id}/approval` |

A request without a valid bearer token gets `401`. A request from a caller
whose JWT `roles` claim doesn't include an allowed role gets `403`.

## Vendors — `/vendors`

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/vendors` | write | Create a vendor |
| GET | `/vendors` | read | List vendors (paginated, filter by `status`) |
| GET | `/vendors/{id}` | read | Get a vendor |
| PATCH | `/vendors/{id}` | write | Update vendor fields / status |
| DELETE | `/vendors/{id}` | write | Soft-delete a vendor |
| GET | `/vendors/{id}/ledger` | read | Full ledger + running balance |
| POST | `/vendors/{id}/ledger` | write | Manual ledger adjustment (e.g. write-off) |

Ledger balance convention: a **debit** entry increases `balance_after`, a
**credit** entry decreases it. Invoices post a credit (amount owed to the
vendor grows more negative); payments post a debit (balance moves back
toward zero). See `SCHEMA.md` for the full rationale.

## Purchase Orders — `/purchase-orders`

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/purchase-orders` | write | Create a PO (status starts `pending_approval`) |
| GET | `/purchase-orders` | read | List (filter by `vendor_id`, `status`) |
| GET | `/purchase-orders/{id}` | read | Get one PO with line items |
| PATCH | `/purchase-orders/{id}` | write | Edit notes/expected delivery (draft/pending only) |
| POST | `/purchase-orders/{id}/approval` | approver | `{"approve": true}` or `{"approve": false, "rejection_reason": "..."}` |
| POST | `/purchase-orders/{id}/cancel` | write | Cancel (not allowed once received/closed) |

### PO status lifecycle
```
draft -> pending_approval -> approved -> partially_received -> received -> closed
                           \-> rejected                                 
approved/partially_received -> cancelled (any time before fully received)
```

## Goods Receipt Notes — `/grn`

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/grn` | write | Record receipt of goods against an **approved** PO |
| GET | `/grn/{id}` | read | Get a GRN with line items |
| GET | `/grn/by-po/{po_id}` | read | List all GRNs recorded against a PO |

Creating a GRN increments `quantity_received` on the matching PO line items
and rolls the parent PO's status forward to `partially_received` or
`received`. Over-receiving (more than the remaining ordered quantity) is
rejected with `400`. Receiving against a PO that isn't `approved` /
`partially_received` is rejected with `409`.

## Purchase Invoices — `/invoices`

| Method | Path | Role | Description |
|---|---|---|---|
| POST | `/invoices` | write | Book an invoice; posts a ledger credit and (if PO+GRN attached) queues an async 3-way match |
| GET | `/invoices` | read | List (filter by `vendor_id`, `status`) |
| GET | `/invoices/{id}` | read | Get one invoice with line items |
| PATCH | `/invoices/{id}/status` | write | Manually move status (e.g. `approved_for_payment`, `paid`) |
| POST | `/invoices/{id}/match` | write | Force-run the PO/GRN/Invoice 3-way match synchronously |

`(vendor_id, invoice_number)` is unique — re-submitting the same invoice
number for the same vendor returns `409`.

### Invoice status lifecycle
```
received -> matched -> approved_for_payment -> paid
         \-> disputed  (mismatched qty/price, or missing PO/GRN refs)
any -> cancelled
```

## Error format

```json
{
  "error": {
    "message": "Vendor not found",
    "status_code": 404
  }
}
```

Validation errors (`422`) include a `details` array with per-field Pydantic
error info.

## Pagination

List endpoints accept `page` (default 1) and `page_size` (default 20, max
100) and return:

```json
{ "items": [...], "total": 42, "page": 1, "page_size": 20 }
```
