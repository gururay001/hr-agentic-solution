import React from 'react';

interface SagaStatusProps {
  status: 'STARTED' | 'HR_COMMITTED' | 'IT_FAILED' | 'COMPLETED' | 'ROLLBACK_EXECUTED';
  hrTxId?: string;
  itTicketId?: string;
}

export const SagaStatusStepper: React.FC<SagaStatusProps> = ({ status, hrTxId, itTicketId }) => {
  return (
    <div className="p-4 bg-white shadow rounded-lg max-w-xl">
      <h3 className="text-lg font-bold mb-4">Cross-Domain Provisioning Progress</h3>
      <ol className="relative border-l border-gray-200 ml-3">
        <li className="mb-6 ml-6">
          <span className={`absolute flex items-center justify-center w-6 h-6 rounded-full -left-3 ring-8 ring-white ${status === 'STARTED' ? 'bg-blue-200' : 'bg-green-500'}`}>
            {status !== 'STARTED' ? '✓' : '•'}
          </span>
          <h4 className="font-semibold text-gray-900">1. WorkWeek HR Update</h4>
          <p className="text-sm text-gray-500">Record updated {hrTxId && `(Tx: ${hrTxId})`}</p>
        </li>
        <li className="mb-6 ml-6">
          <span className={`absolute flex items-center justify-center w-6 h-6 rounded-full -left-3 ring-8 ring-white ${
            status === 'COMPLETED' ? 'bg-green-500' : (status === 'IT_FAILED' || status === 'ROLLBACK_EXECUTED' ? 'bg-red-500' : 'bg-gray-200')
          }`}>
            {status === 'COMPLETED' ? '✓' : (status === 'IT_FAILED' || status === 'ROLLBACK_EXECUTED' ? '✕' : '•')}
          </span>
          <h4 className="font-semibold text-gray-900">2. ServiceImmediately IT Ticket</h4>
          <p className="text-sm text-gray-500">
            {status === 'COMPLETED' ? `Ticket provisioned (${itTicketId})` : (status === 'IT_FAILED' || status === 'ROLLBACK_EXECUTED' ? 'Provisioning Failed' : 'Pending...')}
          </p>
        </li>
        <li className="ml-6">
          <span className={`absolute flex items-center justify-center w-6 h-6 rounded-full -left-3 ring-8 ring-white ${
            status === 'COMPLETED' ? 'bg-green-500' : (status === 'ROLLBACK_EXECUTED' ? 'bg-amber-500' : 'bg-gray-200')
          }`}>
            {status === 'COMPLETED' ? '✓' : (status === 'ROLLBACK_EXECUTED' ? '⚠' : '•')}
          </span>
          <h4 className="font-semibold text-gray-900">3. Finalized / Automatic Rollback Safety</h4>
          <p className="text-sm text-gray-500">
            {status === 'COMPLETED' ? 'Saga completed successfully.' : (
              status === 'ROLLBACK_EXECUTED' ? 'Rollback activated. WorkWeek records have been safely reverted. Support team has been notified via retry tasks.' : 'Awaiting completion.'
            )}
          </p>
        </li>
      </ol>
    </div>
  );
};
