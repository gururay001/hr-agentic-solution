import React, { useState } from 'react';

interface CSATProps {
  sessionId: string;
  onSubmit: (rating: number, feedback: string) => void;
}

export const CSATSurveyCard: React.FC<CSATProps> = ({ sessionId, onSubmit }) => {
  const [rating, setRating] = useState<number>(5);
  const [feedback, setFeedback] = useState<string>('');
  const [submitted, setSubmitted] = useState<boolean>(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(rating, feedback);
    setSubmitted(true);
  };

  if (submitted) {
    return <div className="p-4 bg-green-50 rounded-lg text-green-800">Thank you for your feedback! (Target CSAT >= 4.2/5.0)</div>;
  }

  return (
    <form onSubmit={handleSubmit} className="p-4 bg-white shadow rounded-lg max-w-md">
      <h3 className="text-lg font-semibold mb-2">How was your HR support experience?</h3>
      <div className="flex space-x-2 mb-4">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            type="button"
            key={star}
            onClick={() => setRating(star)}
            className={`text-2xl ${star <= rating ? 'text-yellow-500' : 'text-gray-300'}`}
          >
            ★
          </button>
        ))}
      </div>
      <textarea
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        placeholder="Optional feedback..."
        className="w-full p-2 border rounded mb-2"
      />
      <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
        Submit Rating
      </button>
    </form>
  );
};
