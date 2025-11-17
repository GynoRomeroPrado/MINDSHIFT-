/**
 * Admin Dashboard Component
 * Platform-wide admin panel for system management
 */
import React, { useEffect, useState } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { apiClient } from '../../api/client';

interface SystemStats {
  total_organizations: number;
  total_users: number;
  active_users_7d: number;
  active_users_30d: number;
  total_conversations: number;
  conversations_30d: number;
  total_messages: number;
  messages_30d: number;
  total_checkins: number;
  checkins_30d: number;
  crisis_detections_30d: number;
  high_risk_users: number;
  avg_burnout_score: number;
}

interface Organization {
  id: number;
  name: string;
  domain: string;
  size: number;
  plan_tier: string;
  is_active: boolean;
  total_users: number;
  active_users_30d: number;
  avg_burnout_score: number;
  high_risk_count: number;
  total_conversations: number;
  total_checkins: number;
  created_at: string;
}

export const AdminDashboard: React.FC = () => {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [usageData, setUsageData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'organizations' | 'usage'>('overview');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statsData, orgsData, usageStatsData] = await Promise.all([
        apiClient.getSystemStats(),
        apiClient.getOrganizations(),
        apiClient.getUsageStats(30),
      ]);

      setStats(statsData);
      setOrganizations(orgsData);
      setUsageData(usageStatsData);
    } catch (error) {
      console.error('Failed to load admin data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
        <p className="text-gray-600 mt-1">Platform-wide statistics and management</p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('overview')}
            className={`${
              activeTab === 'overview'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('organizations')}
            className={`${
              activeTab === 'organizations'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
          >
            Organizations
          </button>
          <button
            onClick={() => setActiveTab('usage')}
            className={`${
              activeTab === 'usage'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors`}
          >
            Usage Trends
          </button>
        </nav>
      </div>

      {/* Content */}
      {activeTab === 'overview' && stats && (
        <OverviewTab stats={stats} />
      )}

      {activeTab === 'organizations' && (
        <OrganizationsTab organizations={organizations} onRefresh={loadData} />
      )}

      {activeTab === 'usage' && usageData && (
        <UsageTab usageData={usageData} />
      )}
    </div>
  );
};

// Overview Tab
const OverviewTab: React.FC<{ stats: SystemStats }> = ({ stats }) => {
  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Organizations"
          value={stats.total_organizations.toString()}
          icon="🏢"
          color="blue"
        />
        <MetricCard
          title="Total Users"
          value={stats.total_users.toLocaleString()}
          subtitle={`${stats.active_users_30d} active (30d)`}
          icon="👥"
          color="green"
        />
        <MetricCard
          title="Conversations"
          value={stats.conversations_30d.toLocaleString()}
          subtitle="Last 30 days"
          icon="💬"
          color="purple"
        />
        <MetricCard
          title="High Risk Users"
          value={stats.high_risk_users.toString()}
          subtitle={`Avg: ${stats.avg_burnout_score.toFixed(1)}/100`}
          icon="⚠️"
          color="red"
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Messages"
          value={stats.messages_30d.toLocaleString()}
          total={stats.total_messages.toLocaleString()}
          label="last 30 days"
        />
        <StatCard
          title="Check-ins"
          value={stats.checkins_30d.toLocaleString()}
          total={stats.total_checkins.toLocaleString()}
          label="last 30 days"
        />
        <StatCard
          title="Crisis Detections"
          value={stats.crisis_detections_30d.toString()}
          label="last 30 days"
          color="red"
        />
      </div>

      {/* Activity Indicators */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Activity Overview</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <ActivityIndicator
            label="7-Day Active"
            value={stats.active_users_7d}
            total={stats.total_users}
          />
          <ActivityIndicator
            label="30-Day Active"
            value={stats.active_users_30d}
            total={stats.total_users}
          />
          <ActivityIndicator
            label="Conversation Rate"
            value={stats.conversations_30d}
            total={stats.active_users_30d}
          />
          <ActivityIndicator
            label="Check-in Rate"
            value={stats.checkins_30d}
            total={stats.active_users_30d}
          />
        </div>
      </div>
    </div>
  );
};

// Organizations Tab
const OrganizationsTab: React.FC<{
  organizations: Organization[];
  onRefresh: () => void;
}> = ({ organizations, onRefresh }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredOrgs = organizations.filter(
    (org) =>
      org.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      org.domain.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Search */}
      <div className="bg-white rounded-lg shadow p-4">
        <input
          type="text"
          placeholder="Search organizations..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* Organizations Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Organization
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Plan
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Users
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Activity
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Health
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredOrgs.map((org) => (
              <tr key={org.id} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div>
                    <div className="text-sm font-medium text-gray-900">{org.name}</div>
                    <div className="text-sm text-gray-500">{org.domain}</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                    {org.plan_tier}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {org.total_users} total
                  <br />
                  <span className="text-gray-500">{org.active_users_30d} active</span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  {org.total_conversations} convs
                  <br />
                  <span className="text-gray-500">{org.total_checkins} check-ins</span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm">
                    <div className="font-medium">{org.avg_burnout_score.toFixed(1)}/100</div>
                    {org.high_risk_count > 0 && (
                      <div className="text-red-600">{org.high_risk_count} high risk</div>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span
                    className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                      org.is_active
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    {org.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// Usage Tab
const UsageTab: React.FC<{ usageData: any }> = ({ usageData }) => {
  return (
    <div className="space-y-6">
      {/* Daily Active Users */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Daily Active Users (Last 30 Days)</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={usageData.daily_active_users}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="count" stroke="#6366F1" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Daily Conversations and Check-ins */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Daily Conversations</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={usageData.daily_conversations}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#8B5CF6" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Daily Check-ins</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={usageData.daily_checkins}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#10B981" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

// Helper Components
interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  icon: string;
  color: 'blue' | 'green' | 'purple' | 'red';
}

const MetricCard: React.FC<MetricCardProps> = ({ title, value, subtitle, icon, color }) => {
  const colorClasses = {
    blue: 'bg-blue-50 border-blue-200 text-blue-800',
    green: 'bg-green-50 border-green-200 text-green-800',
    purple: 'bg-purple-50 border-purple-200 text-purple-800',
    red: 'bg-red-50 border-red-200 text-red-800',
  };

  return (
    <div className={`rounded-lg border p-6 ${colorClasses[color]}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-3xl">{icon}</span>
      </div>
      <p className="text-sm font-medium opacity-80 mb-1">{title}</p>
      <p className="text-3xl font-bold">{value}</p>
      {subtitle && <p className="text-sm mt-1 opacity-70">{subtitle}</p>}
    </div>
  );
};

const StatCard: React.FC<{
  title: string;
  value: string;
  total?: string;
  label: string;
  color?: string;
}> = ({ title, value, total, label, color = 'indigo' }) => {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <p className="text-sm font-medium text-gray-600 mb-2">{title}</p>
      <p className={`text-3xl font-bold text-${color}-600`}>{value}</p>
      {total && <p className="text-sm text-gray-500 mt-1">of {total} total</p>}
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  );
};

const ActivityIndicator: React.FC<{
  label: string;
  value: number;
  total: number;
}> = ({ label, value, total }) => {
  const percentage = total > 0 ? Math.round((value / total) * 100) : 0;

  return (
    <div>
      <p className="text-sm text-gray-600 mb-1">{label}</p>
      <p className="text-2xl font-bold text-gray-900">{percentage}%</p>
      <p className="text-xs text-gray-500">
        {value.toLocaleString()} / {total.toLocaleString()}
      </p>
    </div>
  );
};

export default AdminDashboard;
