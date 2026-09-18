# 04. State Machines & Operational Lifecycles

## 1. ServiceRequest (Job Execution) State Machine

Every operational job lifecycle is enforced by server-side state transitions. Invalid transitions are strictly rejected with HTTP 409 Conflict.

```mermaid
stateDiagram-v2
    [*] --> new_request: Booking Created
    new_request --> confirmed: Payment/Details Verified
    confirmed --> assigned: Candidate Matching
    assigned --> accepted: Technician Accepts Offer
    accepted --> on_the_way: Start Trip (GPS Tracking On)
    on_the_way --> arrived: Within 10m Geofence
    arrived --> in_progress: OTP Verified + Pre-photos
    
    state in_progress {
        [*] --> standard_work
        standard_work --> inspection_submitted: On-Site Inspection
        inspection_submitted --> quotation_pending: Vendor Builds Quote
        quotation_pending --> quotation_approved: Customer OTP Accept
        quotation_pending --> quotation_rejected: Customer Declines
        quotation_approved --> standard_work: Continue with Added Scope
        quotation_rejected --> standard_work: Continue with Original Scope
    }
    
    in_progress --> proof_submitted: Post-Service Photos Uploaded
    proof_submitted --> completed: Cash Collected (if COD) & Verified
    completed --> [*]
    
    new_request --> cancelled: Customer / Admin Cancel
    confirmed --> cancelled: Customer / Admin Cancel
    assigned --> cancelled: Auto-Cancel on Timeout
    accepted --> cancelled: Emergency Unassign
    cancelled --> [*]
```

### Transition Validation Rules
| From State | Allowed To State | Required Trigger & Server Validations |
| :--- | :--- | :--- |
| `new_request` | `confirmed` | Initial customer validation & payment authorization. |
| `confirmed` | `assigned` | Automatic or Admin dispatch links candidate `Employee`. |
| `assigned` | `accepted` | Technician accepts `WorkforceJobOffer`; employee flagged as `is_busy = true`. |
| `accepted` | `on_the_way` | Technician clicks "Start Trip"; GPS breadcrumb session initialized. |
| `on_the_way` | `arrived` | Haversine distance to job site must be $\le 10\text{ meters}$. |
| `arrived` | `in_progress` | 6-digit customer start OTP verified + minimum 3 pre-service photos uploaded. |
| `in_progress` | `proof_submitted`| Mandatory post-service photo proof uploaded. |
| `proof_submitted`| `completed` | If `payment_method == 'COD'`, `payment_status` must be `collected`; resets `is_busy = false`. |

---

## 2. WorkforceJobOffer State Machine

Manages candidate offers during automatic dispatch sweeps.

```mermaid
stateDiagram-v2
    [*] --> OFFERED: Spatial Sweep Matches Candidate
    OFFERED --> ACCEPTED: Candidate Accepts (select_for_update)
    OFFERED --> REJECTED: Candidate Declines with Reason
    OFFERED --> EXPIRED: Timeout (5 mins elapsed)
    OFFERED --> CANCELLED: Job Cancelled or Assigned Elsewhere
    
    ACCEPTED --> [*]
    REJECTED --> [*]: Triggers Next-Tier Ring Sweep
    EXPIRED --> [*]: Triggers Next-Tier Ring Sweep
    CANCELLED --> [*]
```

---

## 3. Technician Availability & Shift Lifecycle

Separates attendance (shifts) from real-time operational availability (presence).

```mermaid
stateDiagram-v2
    [*] --> CLOCKED_OUT
    CLOCKED_OUT --> CLOCKED_IN: Clock In (Photo + GPS Location)
    
    state CLOCKED_IN {
        [*] --> OFFLINE
        OFFLINE --> ONLINE: Toggle Presence Online
        ONLINE --> OFFLINE: Toggle Presence Offline
        ONLINE --> BUSY: Accepts Active Job Offer
        BUSY --> ONLINE: Completes Active Job
        ONLINE --> ON_BREAK: Start Break
        ON_BREAK --> ONLINE: End Break
    }
    
    CLOCKED_IN --> CLOCKED_OUT: Clock Out (Blocked if BUSY)
```

---

## 4. Quotation & Additional Work Lifecycle

```mermaid
stateDiagram-v2
    [*] --> DRAFT: Technician Submits Inspection
    DRAFT --> SUBMITTED: Vendor Admin Adds Line Items & Submits
    SUBMITTED --> APPROVED: Customer Enters OTP to Approve
    SUBMITTED --> REJECTED: Customer Declines Additional Work
    SUBMITTED --> EXPIRED: Decision Window Elapsed (24h)
    
    APPROVED --> [*]: Scope Appended to ServiceRequest
    REJECTED --> [*]: Original Scope Maintained
    EXPIRED --> [*]
```

---

## 5. Wallet Withdrawal & Payout Lifecycle

```mermaid
stateDiagram-v2
    [*] --> PENDING: Vendor / Technician Requests Payout
    PENDING --> APPROVED: Finance Admin Reviews & Verifies Bank
    PENDING --> REJECTED: Discrepancy Found / Insufficient Balance
    APPROVED --> PROCESSED: Bank Transfer Reference Recorded (UTR)
    
    PROCESSED --> [*]: Ledger Balance Finalized
    REJECTED --> [*]: Funds Released Back to Available Balance
```
