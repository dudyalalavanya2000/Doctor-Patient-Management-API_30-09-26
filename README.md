# Levels 27–29 – Billing, Reports & Transactions

## LEVEL 27 – Billing Module

### Billing Management

A complete Billing module was implemented to manage patient billing records.

### Billing Fields

* `id`
* `patient_id`
* `doctor_id`
* `appointment_id`
* `consultation_fee`
* `additional_charges`
* `total_amount`
* `payment_status`
* `payment_mode`
* `is_active`
* `created_at`
* `updated_at`

### Billing Business Rules

* Patient must exist before creating a billing record.
* Doctor must exist and be active.
* If an appointment is provided, it must exist.
* The appointment must belong to the specified doctor.
* The appointment must belong to the specified patient.
* Billing cannot be created for a cancelled appointment.
* `total_amount` is calculated automatically from consultation fee and additional charges.
* Duplicate billing for the same appointment is not allowed.
* Only Admin users can create, update, and delete billing records.
* Doctors can view billing records related to their authorized patients.
* Soft delete is used for billing records.

### Billing APIs

| Method | Endpoint                        | Description              |
| :----- | :------------------------------ | :----------------------- |
| POST   | `/api/v1/billings/`             | Create billing           |
| GET    | `/api/v1/billings/`             | List billing records     |
| GET    | `/api/v1/billings/{billing_id}` | Get billing by ID        |
| PUT    | `/api/v1/billings/{billing_id}` | Update billing           |
| PATCH  | `/api/v1/billings/{billing_id}` | Partially update billing |
| DELETE | `/api/v1/billings/{billing_id}` | Soft delete billing      |

---

## LEVEL 28 – Billing Reports & Filtering

### Billing Filters

The Billing list API supports filtering by:

* Payment status
* Doctor ID
* Patient ID
* From date
* To date

### Pagination

Billing list APIs support pagination using:

* `page`
* `limit`

The response provides:

* Total number of records
* Current page
* Page size
* Billing data

### Revenue Reports

A revenue reporting API was implemented to provide:

* Total revenue
* Revenue grouped by doctor
* Revenue grouped by day
* Optional doctor filtering
* Optional date-range filtering

Only **active and paid billing records** are included in revenue calculations.

### Revenue API

```text
GET /api/v1/reports/revenue
```

Example:

```text
GET /api/v1/reports/revenue?doctor_id=1&from=2026-09-01&to=2026-09-30
```

### Revenue Authorization

**Admin**

* Can view overall revenue.
* Can filter revenue by doctor.
* Can filter revenue by date range.

**Doctor**

* Can view only their own revenue.
* Cannot view another doctor's revenue.

---

## LEVEL 29 – Transactions & Consistency

### Database Transactions

The Billing creation process uses a database transaction when creating a billing record and updating the related appointment.

The transaction flow is:

```text
Create Billing Request
        ↓
Validate Doctor & Patient
        ↓
Validate Appointment
        ↓
Check Duplicate Billing
        ↓
Calculate Total Amount
        ↓
Create Billing Record
        ↓
Update Appointment → completed
        ↓
Database Flush
        ↓
Commit Transaction
        ↓
Successful Response
```

### Transaction Consistency

Billing creation and appointment status update are handled together.

If a database operation fails:

* The transaction is rolled back.
* The billing record is not partially created.
* The appointment status update is rolled back.
* The database remains in a consistent state.

### Database-Level Constraints

The following database constraints are implemented:

* Doctor email is unique.
* Billing appointment ID is unique when provided.
* Billing doctor ID is a foreign key.
* Billing patient ID is a foreign key.
* Billing appointment ID is a foreign key.
* Required billing fields cannot be null.
* SQLite foreign-key enforcement is enabled.

### Duplicate Billing Protection

Duplicate billing for the same appointment is prevented at two levels:

1. Application-level duplicate validation.
2. Database-level unique constraint on `appointment_id`.

This provides additional protection against inconsistent billing records.

### Transaction Verification

The transaction flow was verified using Appointment ID `2`.

Initial appointment status:

```text
scheduled
```

Billing request:

```json
{
  "patient_id": 1,
  "doctor_id": 1,
  "appointment_id": 2,
  "consultation_fee": 700,
  "additional_charges": 100,
  "payment_status": "pending",
  "payment_mode": "cash"
}
```

Billing was successfully created with:

```text
Consultation Fee: 700
Additional Charges: 100
Total Amount: 800
```

After successful billing creation, Appointment ID `2` was updated to:

```text
completed
```

This verifies that the Billing creation and Appointment status update were successfully persisted together.

### Error Handling

The transaction implementation handles failures using rollback logic.

```text
Billing / Appointment Operation
        ↓
      Error
        ↓
    Rollback
        ↓
No Partial Changes
```

This ensures database consistency when an operation fails.
