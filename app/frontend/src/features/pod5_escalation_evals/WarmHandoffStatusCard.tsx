import React from 'react';

interface WarmHandoffProps {
  caseId: string;
  queue: string;
}

export const WarmHandoffStatusCard: React.FC<WarmHandoffProps> = ({ caseId, queue }) => {
  return (
    <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg max-w-md">
      <h3 className="font-bold text-amber-900 mb-1">Live HR Specialist Warm Handoff Triggered</h3>
      <p className="text-sm text-amber-800 mb-2">Your case has been escalated to <strong>{queue}</strong>.</p>
      <div className="bg-white p-2 rounded text-xs font-mono mb-2">Case ID: {caseId} | SLA: &lt; 2 hours</div>
      <p className="text-xs text-amber-700">A People Partner is reviewing your DLP-redacted 5-turn conversation summary.</p>
    </div>
  );
};
