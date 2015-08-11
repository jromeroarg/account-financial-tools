# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import fields, models, api, _


class account_statement_move_import_wizard(models.TransientModel):
    _name = "account.statement.move.import.wizard"
    _description = "account_statement_move_import_wizard"

    @api.model
    def _get_statement(self):
        return self.env['account.bank.statement'].browse(
            self._context.get('active_id', False))

    statement_id = fields.Many2one(
        'account.bank.statement',
        'Statement',
        default=_get_statement,
        required=True,
        )
    journal_id = fields.Many2one(
        'account.journal',
        'Journal',
        compute='get_journal',
        )
    journal_account_ids = fields.Many2many(
        'account.account',
        compute='get_accounts',
        string='Journal Accounts'
        )
    move_line_ids = fields.Many2many(
        'account.move.line',
        'account_statement_import_move_line_rel',
        'line_id', 'move_line_id',
        'Journal Items',
        # TODO perhups there is no need to restrict to this journal, only to
        # accounts
        domain="[('journal_id', '=', journal_id), "
        "('statement_id', '=', False), "
        "('account_id', 'in', journal_account_ids[0][2])]"
        )

    @api.multi
    @api.depends('statement_id')
    def get_journal(self):
        self.journal_id = self.statement_id.journal_id

    @api.multi
    @api.depends('journal_id')
    def get_accounts(self):
        self.journal_account_ids = (
            self.journal_id.default_credit_account_id +
            self.journal_id.default_debit_account_id)

    @api.multi
    def confirm(self):
        self.ensure_one()

        statement = self.statement_id

        for line in self.move_line_ids:
            if line.account_id not in self.journal_account_ids:
                raise Warning(_(
                    'Imported line account must be one of the journals '
                    'defaults, in this case %s') % (
                    ', '.join(self.journal_account_ids.mapped('name'))))

            if line.statement_id:
                raise Warning(_(
                    'Imported line must have "statement_id" == False'))

            line_balance = line.debit - line.credit
            # if line_balance > 0:
            #     line_type = 'customer'
            # else:
            #     line_type = 'supplier'

            line_vals = {
                'statement_id': statement.id,
                'name': line.name,
                'ref': line.ref,
                'amount': line_balance,
                'imported': True,
                # 'type': line_type,
                'partner_id': line.partner_id.id,
                # we need journal entry so that id dont suggest a
                # reconciliation
                'journal_entry_id': line.move_id.id,
                }

            # create statement line
            statement.line_ids.create(line_vals)

            # add statement to move lines
            line.move_id.line_id.write({'statement_id': statement.id})
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
