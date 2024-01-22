from trytond.pool import PoolMeta, Pool
from trytond.model import fields


class Employee(metaclass=PoolMeta):
    __name__ = 'company.employee'

    users = fields.Many2Many('res.user-company.employee', 'employee', 'user', 'Users')