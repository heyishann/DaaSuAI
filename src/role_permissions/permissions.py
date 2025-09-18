role_permissions = {
    "admin": {"tables": "*", "columns": "*"},
    "manager": {
        "tables": ["designation", "invitation"],
        "columns": {
            "invitation": ["id", "status", "created_at"],
            "designation": ["id", "name"]
        }
    }
}