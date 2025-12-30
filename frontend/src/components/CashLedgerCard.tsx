type Props = {
  summary: CashLedgerSummary
}

export function CashLedgerCard({ summary }: Props) {
  return (
    <div className="bg-white rounded-xl shadow p-4">
      <h3 className="font-semibold mb-2">Caixa & Split Payment</h3>

      <ul className="space-y-1 text-sm">
        <li>Total em caixa: <b>R$ {summary.total_caixa.toLocaleString()}</b></li>
        <li>Split: <b>{summary.split_percent * 100}%</b></li>
        <li>Pico de caixa: <b>{summary.pico_caixa.period}</b></li>
        <li>Valor do pico: <b>R$ {summary.pico_caixa.value.toLocaleString()}</b></li>
      </ul>
    </div>
  )
}
