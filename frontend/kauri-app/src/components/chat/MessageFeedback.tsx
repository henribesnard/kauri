import React, { useState, useEffect } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { conversationService } from '../../services/conversationService';
import type { MessageFeedbackRequest } from '../../types';

interface MessageFeedbackProps {
  messageId: string;
  currentFeedback?: {
    rating: 'positive' | 'negative';
    comment?: string;
    feedback_at: string;
  };
  onFeedbackSubmitted?: () => void;
}

export const MessageFeedback: React.FC<MessageFeedbackProps> = ({
  messageId,
  currentFeedback,
  onFeedbackSubmitted,
}) => {
  const [selectedRating, setSelectedRating] = useState<'positive' | 'negative' | null>(
    currentFeedback?.rating || null
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showCommentInput, setShowCommentInput] = useState(false);
  const [comment, setComment] = useState(currentFeedback?.comment || '');

  // Sync state with currentFeedback prop when it changes
  useEffect(() => {
    setSelectedRating(currentFeedback?.rating || null);
    setComment(currentFeedback?.comment || '');
  }, [currentFeedback]);

  const handleFeedback = async (rating: 'positive' | 'negative') => {
    if (isSubmitting) return;

    // If clicking the same rating, show comment input
    if (selectedRating === rating) {
      setShowCommentInput(!showCommentInput);
      return;
    }

    setIsSubmitting(true);

    try {
      const feedbackData: MessageFeedbackRequest = {
        rating,
        comment: comment.trim() || undefined,
      };

      await conversationService.addMessageFeedback(messageId, feedbackData);
      setSelectedRating(rating);
      setShowCommentInput(false);

      if (onFeedbackSubmitted) {
        onFeedbackSubmitted();
      }
    } catch (error) {
      console.error('Erreur lors de l\'envoi du feedback:', error);
      alert('Erreur lors de l\'envoi du feedback. Veuillez réessayer.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmitComment = async () => {
    if (!selectedRating || isSubmitting) return;

    setIsSubmitting(true);

    try {
      const feedbackData: MessageFeedbackRequest = {
        rating: selectedRating,
        comment: comment.trim() || undefined,
      };

      await conversationService.addMessageFeedback(messageId, feedbackData);
      setShowCommentInput(false);

      if (onFeedbackSubmitted) {
        onFeedbackSubmitted();
      }
    } catch (error) {
      console.error('Erreur lors de l\'envoi du commentaire:', error);
      alert('Erreur lors de l\'envoi du commentaire. Veuillez réessayer.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mt-2">
      <div className="flex items-center gap-2">
        <button
          onClick={() => handleFeedback('positive')}
          disabled={isSubmitting}
          className={`p-1 rounded transition ${
            selectedRating === 'positive'
              ? 'text-green-600 bg-green-50'
              : 'text-gray-400 hover:text-green-600 hover:bg-green-50'
          } disabled:opacity-50`}
          title="Réponse utile"
        >
          <ThumbsUp size={16} />
        </button>
        <button
          onClick={() => handleFeedback('negative')}
          disabled={isSubmitting}
          className={`p-1 rounded transition ${
            selectedRating === 'negative'
              ? 'text-red-600 bg-red-50'
              : 'text-gray-400 hover:text-red-600 hover:bg-red-50'
          } disabled:opacity-50`}
          title="Réponse peu utile"
        >
          <ThumbsDown size={16} />
        </button>
        {selectedRating && (
          <span className="text-xs text-gray-500">
            Merci pour votre retour !
          </span>
        )}
      </div>

      {showCommentInput && (
        <div className="mt-2 space-y-2">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Commentaire optionnel..."
            className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-green-500 focus:border-transparent resize-none"
            rows={3}
            maxLength={1000}
          />
          <div className="flex justify-end gap-2">
            <button
              onClick={() => setShowCommentInput(false)}
              className="px-3 py-1 text-sm text-gray-600 hover:text-gray-800"
              disabled={isSubmitting}
            >
              Annuler
            </button>
            <button
              onClick={handleSubmitComment}
              className="px-3 py-1 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
              disabled={isSubmitting}
            >
              Envoyer
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
