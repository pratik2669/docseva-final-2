# DocSeva role separation

DocSeva now separates application roles from Django technical superuser access.

## Roles

| Role | Portal | Capabilities |
|---|---|---|
| User | `/dashboard/` | Own profile, documents, renewal, emergency QR, support, sharing |
| Admin | `/portal/admin/` | Operational admin: users, documents, tickets, appointments, security logs |
| Super Admin | `/portal/admin/` | Admin features plus ability to change portal roles |
| Django superuser | `/admin/` | Technical database/admin maintenance only |

## Create roles

```bash
python manage.py set_portal_role username user
python manage.py set_portal_role username admin
python manage.py set_portal_role username superadmin
```

Backward-compatible command:

```bash
python manage.py promote_portal_admin username --role admin
python manage.py promote_portal_admin username --role superadmin
```

## Rule

Normal Admins cannot promote/demote admins. Only Super Admins can change `portal_role`.
