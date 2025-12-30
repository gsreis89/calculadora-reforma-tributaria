type Props = {
  summary: CreditLedgerSummary
}

export function CreditLedgerCard({ summary }: Props) {
  return (
    <div className="bg-white rounded-xl shadow p-4">
      <h3 className="font-semibold mb-2">Créditos (Não Cumulatividade)</h3>

      <ul className="space-y-1 text-sm">
        <li>Crédito gerado: <b>R$ {summary.credito_gerado.toLocaleString()}</b></li>
        <li>Glosa: <b>R$ {summary.glosa.toLocaleString()}</b></li>
        <li>Crédito apropriado: <b>R$ {summary.credito_apropriado.toLocaleString()}</b></li>
        <li>Saldo a apropriar: <b>R$ {summary.saldo_a_apropriar.toLocaleString()}</b></li>
      </ul>
    </div>
  )
}
