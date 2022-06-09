"""
Temporary patch needed because of this issue: https://github.com/tiangolo/sqlmodel/issues/189
"""


from sqlmodel.sql.expression import Select, SelectOfScalar

SelectOfScalar.inherit_cache = True  # type: ignore
Select.inherit_cache = True  # type: ignore
