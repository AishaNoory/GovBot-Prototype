"use client"

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api-client'
import { 
  UserDemographics, 
  TrafficMetrics, 
  SystemHealth, 
  ROIMetrics, 
  ContainmentRate,
  BusinessFlowSuccess 
} from '@/lib/types'

export function AnalyticsDashboard() {
  const [userDemographics, setUserDemographics] = useState<UserDemographics | null>(null)
  const [trafficMetrics, setTrafficMetrics] = useState<TrafficMetrics | null>(null)
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [roiMetrics, setROIMetrics] = useState<ROIMetrics | null>(null)
  const [containmentRate, setContainmentRate] = useState<ContainmentRate | null>(null)
  const [businessFlowSuccess, setBusinessFlowSuccess] = useState<BusinessFlowSuccess | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadAnalytics()
  }, [])

  const loadAnalytics = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const [
        demographics,
        traffic,
        health,
        roi,
        containment,
        businessFlow
      ] = await Promise.all([
        apiClient.getUserDemographics().catch(() => null),
        apiClient.getTrafficMetrics().catch(() => null),
        apiClient.getSystemHealth().catch(() => null),
        apiClient.getROIMetrics().catch(() => null),
        apiClient.getContainmentRate().catch(() => null),
        apiClient.getBusinessFlowSuccess().catch(() => null)
      ])

      setUserDemographics(demographics)
      setTrafficMetrics(traffic)
      setSystemHealth(health)
      setROIMetrics(roi)
      setContainmentRate(containment)
      setBusinessFlowSuccess(businessFlow)
    } catch (err) {
      setError('Failed to load analytics data')
      console.error('Analytics loading error:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <div className="text-sm text-muted-foreground">Loading analytics...</div>
        </div>
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="rounded-lg border bg-card p-6 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
              <div className="h-8 bg-gray-200 rounded w-3/4"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <button 
            onClick={loadAnalytics}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-red-600 mb-2">{error}</p>
          <p className="text-sm text-red-500">Make sure the analytics service is running on port 8005</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
          <p className="text-muted-foreground">Comprehensive insights into your GovStack system performance</p>
        </div>
        <button 
          onClick={loadAnalytics}
          className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Refresh
        </button>
      </div>

      {/* Key Performance Indicators */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {/* User Demographics */}
        {userDemographics && (
          <div className="rounded-lg border bg-card p-6">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Total Users</h3>
            <div className="text-2xl font-bold">{userDemographics.total_users.toLocaleString()}</div>
            <div className="text-sm text-green-600 mt-1">
              +{userDemographics.user_growth_rate}% growth
            </div>
          </div>
        )}

        {/* Traffic Metrics */}
        {trafficMetrics && (
          <div className="rounded-lg border bg-card p-6">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">Total Sessions</h3>
            <div className="text-2xl font-bold">{trafficMetrics.total_sessions.toLocaleString()}</div>
            <div className="text-sm text-muted-foreground mt-1">
              {trafficMetrics.unique_users.toLocaleString()} unique users
            </div>
          </div>
        )}

        {/* System Health */}
        {systemHealth && (
          <div className="rounded-lg border bg-card p-6">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">System Health</h3>
            <div className="text-2xl font-bold">{systemHealth.uptime_percentage}%</div>
            <div className={`text-sm mt-1 ${
              systemHealth.system_availability === 'healthy' ? 'text-green-600' : 'text-red-600'
            }`}>
              {systemHealth.system_availability}
            </div>
          </div>
        )}

        {/* ROI Metrics */}
        {roiMetrics && (
          <div className="rounded-lg border bg-card p-6">
            <h3 className="text-sm font-medium text-muted-foreground mb-2">ROI</h3>
            <div className="text-2xl font-bold">{roiMetrics.roi_percentage.toFixed(1)}%</div>
            <div className="text-sm text-green-600 mt-1">
              ${roiMetrics.cost_savings.toLocaleString()} saved
            </div>
          </div>
        )}
      </div>

      {/* Detailed Analytics */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* User Analytics */}
        {userDemographics && (
          <div className="rounded-lg border bg-card p-6">
            <h3 className="text-lg font-semibold mb-4">User Analytics</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">New Users</span>
                <span className="font-medium">{userDemographics.new_users.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Returning Users</span>
                <span className="font-medium">{userDemographics.returning_users.toLocaleString()}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Active Users</span>
                <span className="font-medium">{userDemographics.active_users.toLocaleString()}</span>
              </div>
            </div>
          </div>
        )}

        {/* Service Performance */}
        {containmentRate && (
          <div className="rounded-lg border bg-card p-6">
            <h3 className="text-lg font-semibold mb-4">Service Performance</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">Full Automation Rate</span>
                <span className="font-medium text-green-600">{containmentRate.full_automation_rate}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Partial Automation Rate</span>
                <span className="font-medium text-yellow-600">{containmentRate.partial_automation_rate}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Human Handoff Rate</span>
                <span className="font-medium text-red-600">{containmentRate.human_handoff_rate}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Resolution Success Rate</span>
                <span className="font-medium">{containmentRate.resolution_success_rate}%</span>
              </div>
            </div>
          </div>
        )}

        {/* System Performance */}
        {systemHealth && (
          <div className="rounded-lg border bg-card p-6">
            <h3 className="text-lg font-semibold mb-4">System Performance</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">Response Time (P50)</span>
                <span className="font-medium">{systemHealth.api_response_time_p50}ms</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Response Time (P95)</span>
                <span className="font-medium">{systemHealth.api_response_time_p95}ms</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Error Rate</span>
                <span className={`font-medium ${systemHealth.error_rate > 5 ? 'text-red-600' : 'text-green-600'}`}>
                  {systemHealth.error_rate}%
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Business Metrics */}
        {businessFlowSuccess && (
          <div className="rounded-lg border bg-card p-6">
            <h3 className="text-lg font-semibold mb-4">Business Metrics</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">Service Completion Rate</span>
                <span className="font-medium">{businessFlowSuccess.service_completion_rate}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Document Access Success</span>
                <span className="font-medium">{businessFlowSuccess.document_access_success}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Information Accuracy</span>
                <span className="font-medium">{businessFlowSuccess.information_accuracy}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Citizen Satisfaction</span>
                <span className="font-medium">{businessFlowSuccess.citizen_satisfaction_proxy}/5</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Cost Analysis */}
      {roiMetrics && (
        <div className="rounded-lg border bg-card p-6">
          <h3 className="text-lg font-semibold mb-4">Cost Analysis</h3>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">
                ${roiMetrics.cost_per_interaction.toFixed(3)}
              </div>
              <div className="text-sm text-muted-foreground">Cost per interaction</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">
                {roiMetrics.automation_rate}%
              </div>
              <div className="text-sm text-muted-foreground">Automation rate</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">
                ${roiMetrics.cost_savings.toLocaleString()}
              </div>
              <div className="text-sm text-muted-foreground">Total savings</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
