/**
 * Daily Wellbeing Check-In Component
 * Allows users to log their daily mood, stress, energy, sleep, and workload
 */
import React, { useState } from 'react';
import { apiClient } from '../../api/client';

interface CheckInData {
  mood: number;
  energy: number;
  stress: number;
  sleep: number;
  workload: number;
  notes: string;
}

export const DailyCheckIn: React.FC = () => {
  const [checkIn, setCheckIn] = useState<CheckInData>({
    mood: 5,
    energy: 5,
    stress: 5,
    sleep: 5,
    workload: 5,
    notes: '',
  });
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSliderChange = (field: keyof CheckInData, value: number) => {
    setCheckIn((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await apiClient.submitCheckIn(checkIn);
      setSubmitted(true);

      // Reset form after 2 seconds
      setTimeout(() => {
        setSubmitted(false);
        setCheckIn({
          mood: 5,
          energy: 5,
          stress: 5,
          sleep: 5,
          workload: 5,
          notes: '',
        });
      }, 2000);
    } catch (error) {
      console.error('Failed to submit check-in:', error);
      alert('Failed to submit check-in. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-8 max-w-2xl mx-auto">
        <div className="text-center">
          <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
            <svg
              className="h-6 w-6 text-green-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Thank you for checking in!
          </h3>
          <p className="text-gray-600">
            Your wellbeing data helps us support you better.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-8 max-w-2xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Daily Check-In</h2>
        <p className="text-gray-600 mt-1">
          Take a moment to reflect on how you're feeling today
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Mood */}
        <SliderQuestion
          label="How is your mood today?"
          value={checkIn.mood}
          onChange={(value) => handleSliderChange('mood', value)}
          lowLabel="Very Low"
          highLabel="Excellent"
          emoji={getMoodEmoji(checkIn.mood)}
        />

        {/* Energy */}
        <SliderQuestion
          label="What's your energy level?"
          value={checkIn.energy}
          onChange={(value) => handleSliderChange('energy', value)}
          lowLabel="Exhausted"
          highLabel="Energized"
          emoji={getEnergyEmoji(checkIn.energy)}
        />

        {/* Stress */}
        <SliderQuestion
          label="How stressed are you feeling?"
          value={checkIn.stress}
          onChange={(value) => handleSliderChange('stress', value)}
          lowLabel="Not Stressed"
          highLabel="Very Stressed"
          emoji={getStressEmoji(checkIn.stress)}
          inverse
        />

        {/* Sleep */}
        <SliderQuestion
          label="How was your sleep quality?"
          value={checkIn.sleep}
          onChange={(value) => handleSliderChange('sleep', value)}
          lowLabel="Poor"
          highLabel="Excellent"
          emoji={getSleepEmoji(checkIn.sleep)}
        />

        {/* Workload */}
        <SliderQuestion
          label="How heavy is your workload?"
          value={checkIn.workload}
          onChange={(value) => handleSliderChange('workload', value)}
          lowLabel="Light"
          highLabel="Overwhelming"
          emoji={getWorkloadEmoji(checkIn.workload)}
          inverse
        />

        {/* Notes */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Additional notes (optional)
          </label>
          <textarea
            value={checkIn.notes}
            onChange={(e) => setCheckIn((prev) => ({ ...prev, notes: e.target.value }))}
            rows={3}
            className="w-full border border-gray-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            placeholder="Anything else you'd like to share about how you're feeling?"
          />
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-indigo-600 text-white py-3 rounded-lg font-semibold hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Submitting...' : 'Submit Check-In'}
        </button>
      </form>

      <div className="mt-6 p-4 bg-blue-50 rounded-lg">
        <p className="text-sm text-blue-800">
          <strong>Privacy:</strong> Your check-in data is encrypted and confidential. It's only
          used to provide you with personalized support and insights.
        </p>
      </div>
    </div>
  );
};

interface SliderQuestionProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
  lowLabel: string;
  highLabel: string;
  emoji: string;
  inverse?: boolean; // For questions where higher is worse (stress, workload)
}

const SliderQuestion: React.FC<SliderQuestionProps> = ({
  label,
  value,
  onChange,
  lowLabel,
  highLabel,
  emoji,
  inverse = false,
}) => {
  const getSliderColor = () => {
    if (inverse) {
      // For stress/workload - high is bad
      if (value <= 3) return 'bg-green-500';
      if (value <= 6) return 'bg-yellow-500';
      return 'bg-red-500';
    } else {
      // For mood/energy/sleep - high is good
      if (value <= 3) return 'bg-red-500';
      if (value <= 6) return 'bg-yellow-500';
      return 'bg-green-500';
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-3">
        <label className="text-sm font-medium text-gray-700">{label}</label>
        <span className="text-3xl">{emoji}</span>
      </div>

      <div className="relative">
        <input
          type="range"
          min="1"
          max="10"
          value={value}
          onChange={(e) => onChange(parseInt(e.target.value))}
          className="w-full h-2 rounded-lg appearance-none cursor-pointer accent-indigo-600"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-2">
          <span>{lowLabel}</span>
          <span className="font-semibold text-lg text-gray-900">{value}/10</span>
          <span>{highLabel}</span>
        </div>
      </div>

      {/* Visual indicator */}
      <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${getSliderColor()} transition-all duration-300`}
          style={{ width: `${value * 10}%` }}
        ></div>
      </div>
    </div>
  );
};

// Emoji helpers
function getMoodEmoji(value: number): string {
  if (value <= 2) return '😢';
  if (value <= 4) return '😕';
  if (value <= 6) return '😐';
  if (value <= 8) return '🙂';
  return '😊';
}

function getEnergyEmoji(value: number): string {
  if (value <= 3) return '😴';
  if (value <= 6) return '😌';
  return '⚡';
}

function getStressEmoji(value: number): string {
  if (value <= 3) return '😌';
  if (value <= 6) return '😰';
  return '😫';
}

function getSleepEmoji(value: number): string {
  if (value <= 3) return '😴';
  if (value <= 6) return '😪';
  return '✨';
}

function getWorkloadEmoji(value: number): string {
  if (value <= 3) return '📝';
  if (value <= 6) return '📚';
  return '🔥';
}

export default DailyCheckIn;
