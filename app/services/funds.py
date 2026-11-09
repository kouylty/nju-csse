"""Simulated payment and settlement; the order service owns the transaction."""

from app.clock import now, timestamp
from app.errors import BusinessError
from app.repositories import funds


class FundService:
    def __init__(self, conn, *, clock=now):
        self.conn, self.clock = conn, clock

    def get_escrow(self, order_id):
        rows = [dict(row) for row in funds.list_for(self.conn, order_id)]
        totals = {
            kind: sum(row["amount_cents"] for row in rows if row["kind"] == kind)
            for kind in ["PAYMENT", "REFUND", "SETTLEMENT"]
        }
        balance = totals["PAYMENT"] - totals["REFUND"] - totals["SETTLEMENT"]
        if balance < 0:
            raise BusinessError("INVARIANT_VIOLATION", "订单资金记录不一致。")
        return {
            "paid_cents": totals["PAYMENT"],
            "refunded_cents": totals["REFUND"],
            "settled_cents": totals["SETTLEMENT"],
            "balance_cents": balance,
            "transactions": rows,
        }

    def record_payment_in_tx(self, order, actor_id):
        return self._record(order, "PAYMENT", actor_id)

    def refund_all_in_tx(self, order, actor_id):
        self._require_transaction()
        if (
            funds.by_kind(self.conn, order["id"], "REFUND") is None
            and self.get_escrow(order["id"])["balance_cents"] != order["total_cents"]
        ):
            raise BusinessError("INVARIANT_VIOLATION", "平台暂存金额不匹配，本次退款已撤销。")
        return self._record(order, "REFUND", actor_id)

    def settle_in_tx(self, order, actor_id):
        self._require_transaction()
        existing = funds.by_kind(self.conn, order["id"], "SETTLEMENT")
        if (
            existing is None
            and self.get_escrow(order["id"])["balance_cents"] != order["total_cents"]
        ):
            raise BusinessError("INVARIANT_VIOLATION", "平台暂存金额不匹配，本次操作已撤销。")
        return self._record(order, "SETTLEMENT", actor_id)

    def _record(self, order, kind, actor_id):
        self._require_transaction()
        existing = funds.by_kind(self.conn, order["id"], kind)
        if existing is not None:
            if existing["amount_cents"] != order["total_cents"]:
                raise BusinessError("INVARIANT_VIOLATION", "订单资金金额不匹配。")
            return existing["id"]
        return funds.insert(
            self.conn,
            order_id=order["id"],
            kind=kind,
            amount_cents=order["total_cents"],
            actor_id=actor_id,
            created_at=timestamp(self.clock()),
        )

    def _require_transaction(self):
        if not self.conn.in_transaction:
            raise RuntimeError("Fund writes require the caller's transaction")
