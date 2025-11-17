/**
 * Organization Health Dashboard Component
 * Displays high-level organization wellbeing metrics
 */
import React, { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
} from 'recharts';
import { apiClient } from '../../api/client';

interface TeamAnalytics {
  total_employees: number;
  average_score: number;
  risk_distribution: {
    low: number;
    moderate: number;
    high: number;
    critical: number;
  };
  top_contributing_factors: Array<{
    category: string;
    count: number;
  }>;
  high_risk_count: number;
  timestamp: string;
}

const RISK_COLORS = {
  low: '#10B981',     // Green
  moderate: '#F59E0B', // Yellow
  high: '#EF4444',     // Red
  critical: '#991B1B', // Dark Red
};

export const OrganizationHealth: React.FC = () => {
  const [analytics, setAnalytics] = useState<TeamAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      const data = await apiClient.getTeamAnalytics();
      setAnalytics(data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load analytics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">{error}</p>
      </div>
    );
  }

  if (!analytics) {
    return null;
  }

  // Prepare data for charts
  const riskDistributionData = [
    { name: 'Low Risk', value: analytics.risk_distribution.low, color: RISK_COLORS.low },
    { name: 'Moderate Risk', value: analytics.risk_distribution.moderate, color: RISK_COLORS.moderate },
    { name: 'High Risk', value: analytics.risk_distribution.high, color: RISK_COLORS.high },
    { name: 'Critical Risk', value: analytics.risk_distribution.critical, color: RISK_COLORS.critical },
  ];

  const contributingFactorsData = analytics.top_contributing_factors.map((factor) => ({
    name: factor.category.replace(/_/g, ' ').toUpperCase(),
    count: factor.count,
  }));

  // Calculate health score (inverse of average burnout score)
  const healthScore = Math.round(100 - analytics.average_score);

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard
          title="Organization Health"
          value={`${healthScore}%`}
          trend={healthScore > 70 ? 'up' : healthScore > 50 ? 'stable' : 'down'}
          color={healthScore > 70 ? 'green' : healthScore > 50 ? 'yellow' : 'red'}
        />
        <StatCard
          title="Total Employees"
          value={analytics.total_employees.toString()}
          subtitle="Monitored"
          color="blue"
        />
        <StatCard
          title="Average Burnout Risk"
          value={`${Math.round(analytics.average_score)}/100`}
          color={analytics.average_score < 40 ? 'green' : analytics.average_score < 60 ? 'yellow' : 'red'}
        />
        <StatCard
          title="High Risk Employees"
          value={analytics.high_risk_count.toString()}
          subtitle="Require attention"
          color={analytics.high_risk_count > 10 ? 'red' : analytics.high_risk_count > 5 ? 'yellow' : 'green'}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Distribution Pie Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Risk Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={riskDistributionData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {riskDistributionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Contributing Factors Bar Chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Top Contributing Factors</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={contributingFactorsData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#6366F1" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recommendations */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Recommendations</h3>
        <div className="space-y-3">
          {analytics.high_risk_count > 10 && (
            <RecommendationCard
              title="High Risk Alert"
              description={`${analytics.high_risk_count} employees are at high risk of burnout. Consider immediate interventions.`}
              action="Review High-Risk Employees"
              priority="high"
            />
          )}
          {analytics.top_contributing_factors[0]?.category === 'work_life_balance' && (
            <RecommendationCard
              title="Work-Life Balance Initiative"
              description="Work-life balance is the top contributing factor. Consider implementing flexible work policies."
              action="Review Policies"
              priority="medium"
            />
          )}
          {analytics.average_score > 60 && (
            <RecommendationCard
              title="Organization-Wide Support"
              description="Average burnout risk is elevated. Consider organization-wide wellness initiatives."
              action="Plan Initiative"
              priority="medium"
            />
          )}
        </div>
      </div>
    </div>
  );
};

interface StatCardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'stable';
  color?: 'green' | 'yellow' | 'red' | 'blue';
}

const StatCard: React.FC<StatCardProps> = ({ title, value, subtitle, trend, color = 'blue' }) => {
  const colorClasses = {
    green: 'bg-green-50 text-green-800 border-green-200',
    yellow: 'bg-yellow-50 text-yellow-800 border-yellow-200',
    red: 'bg-red-50 text-red-800 border-red-200',
    blue: 'bg-blue-50 text-blue-800 border-blue-200',
  };

  return (
    <div className={`rounded-lg border p-6 ${colorClasses[color]}`}>
      <p className="text-sm font-medium opacity-80">{title}</p>
      <p className="text-3xl font-bold mt-2">{value}</p>
      {subtitle && <p className="text-sm mt-1 opacity-70">{subtitle}</p>}
      {trend && (
        <div className="mt-2">
          {trend === 'up' && <span className="text-xs">↗ Improving</span>}
          {trend === 'down' && <span className="text-xs">↘ Declining</span>}
          {trend === 'stable' && <span className="text-xs">→ Stable</span>}
        </div>
      )}
    </div>
  );
};

interface RecommendationCardProps {
  title: string;
  description: string;
  action: string;
  priority: 'low' | 'medium' | 'high';
}

const RecommendationCard: React.FC<RecommendationCardProps> = ({
  title,
  description,
  action,
  priority
}) => {
  const priorityColors = {
    low: 'border-blue-300 bg-blue-50',
    medium: 'border-yellow-300 bg-yellow-50',
    high: 'border-red-300 bg-red-50',
  };

  return (
    <div className={`border-l-4 p-4 ${priorityColors[priority]}`}>
      <h4 className="font-semibold">{title}</h4>
      <p className="text-sm mt-1 opacity-80">{description}</p>
      <button className="mt-2 text-sm font-medium text-indigo-600 hover:text-indigo-800">
        {action} →
      </button>
    </div>
  );
};

export default OrganizationHealth;
