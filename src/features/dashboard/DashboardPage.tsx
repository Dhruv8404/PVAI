import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Users, 
  UserCheck, 
  FileText, 
  Download, 
  Activity,
  Layers,
  ChevronRight,
  RefreshCw,
  Cpu,
  Mail,
  Clock
} from 'lucide-react';
import { mockDb } from '../../lib/mockDb';
import { useAuth } from '../../context/AuthContext';
import { StatCard } from '../../components/shared/StatCard';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';

export const DashboardPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [metrics, setMetrics] = useState<any>(null);
  const [activities, setActivities] = useState<any[]>([]);
  const [chartsData, setChartsData] = useState<any>(null);
  const [recentUsers, setRecentUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);


  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('pv_token');
      if (token) {
        const res = await fetch('http://127.0.0.1:8000/api/v1/dashboard', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const json = await res.json();
        if (json.success && json.data) {
          const { metrics: m, recent_activities, charts, recent_users } = json.data;
          setMetrics({
            totalUsers: m.total_users,
            activeUsers: m.active_users,
            inactiveUsers: m.inactive_users,
            genToday: m.gen_today,
            genMonth: m.gen_month,
            totalDownloads: m.total_downloads
          });
          
          const mappedLogs = recent_activities.map((a: any) => ({
            id: a.id,
            userName: a.userName || a.user_name || 'System User',
            action: a.action,
            details: a.details,
            timestamp: a.timestamp
          }));
          setActivities(mappedLogs);
          setChartsData(charts);
          setRecentUsers(recent_users || []);
          setLoading(false);
          return;
        }
      }
    } catch (err: any) {
      console.warn('API error in dashboard loader, falling back to mockDb:', err.message);
    }

    const allUsers = mockDb.getUsers();
    const documents = mockDb.getDocuments();
    const logs = mockDb.getAuditLogs();

    if (user?.role === 'Admin') {
      const totalUsers = allUsers.length;
      const activeUsers = allUsers.filter(u => u.status === 'Active').length;
      const inactiveUsers = allUsers.filter(u => u.status === 'Inactive').length;

      const todayStr = new Date().toISOString().substring(0, 10);
      const genToday = documents.filter(d => d.generatedTime.substring(0, 10) === todayStr).length;
      const genMonth = documents.length; 

      const totalDownloads = documents.filter(d => d.downloaded).length;

      setMetrics({
        totalUsers,
        activeUsers,
        inactiveUsers,
        genToday,
        genMonth,
        totalDownloads,
      });

      const dailyGenData = [
        { label: 'Mon', value: 12 },
        { label: 'Tue', value: 18 },
        { label: 'Wed', value: 15 },
        { label: 'Thu', value: 24 },
        { label: 'Fri', value: 30 + genToday },
        { label: 'Sat', value: 8 },
        { label: 'Sun', value: 5 },
      ];
      
      const userGrowth = [
        { label: 'Jan', value: 2 },
        { label: 'Feb', value: 3 },
        { label: 'Mar', value: 4 },
        { label: 'Apr', value: 5 },
        { label: 'May', value: 6 },
        { label: 'Jun', value: totalUsers },
      ];

      setChartsData({
        daily_documents: dailyGenData,
        user_growth: userGrowth
      });

      const recentUsersSorted = [...allUsers]
        .sort((a, b) => new Date(b.createdDate || '').getTime() - new Date(a.createdDate || '').getTime())
        .slice(0, 5)
        .map(u => ({
          id: u.id,
          name: u.name,
          email: u.email,
          status: u.status,
          created_at: u.createdDate
        }));
      setRecentUsers(recentUsersSorted);

      setActivities(logs.slice(0, 5));
    } else {
      const todayStr = new Date().toISOString().substring(0, 10);
      const userDocs = documents.filter(d => d.createdById === user?.id);
      const genToday = userDocs.filter(d => d.generatedTime.substring(0, 10) === todayStr).length;
      const genMonth = userDocs.length; 
      const totalDownloads = userDocs.filter(d => d.downloaded).length;

      setMetrics({
        totalUsers: 0,
        activeUsers: 0,
        inactiveUsers: 0,
        genToday,
        genMonth,
        totalDownloads,
      });

      const dailyGenData = [
        { label: 'Mon', value: 1 },
        { label: 'Tue', value: 2 },
        { label: 'Wed', value: 1 },
        { label: 'Thu', value: 3 },
        { label: 'Fri', value: 2 + genToday },
        { label: 'Sat', value: 0 },
        { label: 'Sun', value: 0 },
      ];

      setChartsData({
        daily_documents: dailyGenData,
        user_growth: []
      });

      setRecentUsers([]);

      const userLogs = logs.filter(l => l.userId === user?.id);
      setActivities(userLogs.slice(0, 5));
    }

    setLoading(false);
  };

  useEffect(() => {
    fetchDashboardData();
  }, [user]);



  // Graph Data points for Daily Documents
  const dailyGenData = chartsData?.daily_documents || [
    { label: 'Mon', value: 0 },
    { label: 'Tue', value: 0 },
    { label: 'Wed', value: 0 },
    { label: 'Thu', value: 0 },
    { label: 'Fri', value: 0 },
    { label: 'Sat', value: 0 },
    { label: 'Sun', value: 0 },
  ];

  const maxGenValue = Math.max(...dailyGenData.map((d: any) => d.value)) || 1;





  return (
    <div className="space-y-6">
      {/* Top Banner with Quick refresh and systems status */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 dark:text-zinc-50 leading-tight">
            Dashboard Overview
          </h1>
          <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1 font-medium">
            Welcome back, <span className="font-bold text-indigo-600 dark:text-indigo-400">{user?.name}</span>. Here is your operations snapshot.
          </p>
        </div>

        <div className="flex items-center gap-3.5">
          <Badge variant="success" className="py-1 px-3 flex gap-1.5 items-center">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[10px] font-bold uppercase tracking-wider">All Systems Operational</span>
          </Badge>

          <Button 
            variant="outline" 
            size="sm" 
            onClick={fetchDashboardData}
            isLoading={loading}
            className="flex-shrink-0"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {/* Grid of Stat Cards */}
      {metrics && user?.role === 'Admin' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            title="Total Users" 
            value={metrics.totalUsers} 
            icon={<Users className="h-5 w-5" />} 
            trend={{ value: '+8% this week', direction: 'up' }}
          />
          <StatCard 
            title="Active Seats" 
            value={metrics.activeUsers} 
            icon={<UserCheck className="h-5 w-5" />} 
            description="Active login sessions"
          />
          <StatCard 
            title="Generated Today" 
            value={metrics.genToday} 
            icon={<FileText className="h-5 w-5" />} 
            trend={metrics.genToday > 2 ? { value: '+20% vs yesterday', direction: 'up' } : undefined}
            description="Reports compiled today"
          />
          <StatCard 
            title="Downloads Vault" 
            value={metrics.totalDownloads} 
            icon={<Download className="h-5 w-5" />} 
            trend={{ value: '62% download rate', direction: 'neutral' }}
          />
        </div>
      )}

      {metrics && user?.role !== 'Admin' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard 
            title="Total Generated" 
            value={user?.documentsGenerated || 0} 
            icon={<FileText className="h-5 w-5" />} 
            description="Your generated documents"
          />
          <StatCard 
            title="Generated Today" 
            value={metrics.genToday} 
            icon={<Activity className="h-5 w-5" />} 
            description="Your documents generated today"
          />
          <StatCard 
            title="Downloads" 
            value={metrics.totalDownloads} 
            icon={<Download className="h-5 w-5" />} 
            description="Your downloaded documents"
          />
          <StatCard 
            title="Tokens Remaining" 
            value={Math.max(0, (user?.reportLimit || 5) - (user?.documentsGenerated || 0))} 
            icon={<Cpu className="h-5 w-5" />} 
            description="Remaining generation quota tokens"
          />
        </div>
      )}

      {/* Graphical Charts Section */}
      <div className={`grid grid-cols-1 ${user?.role === 'Admin' ? 'lg:grid-cols-2' : ''} gap-6`}>
        {/* Daily generated documents (SVG Custom Bars) */}
        <Card>
          <CardHeader>
            <CardTitle>Daily Generated Documents</CardTitle>
            <CardDescription>Activity metrics compiled over the last 7 days.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-48 w-full flex items-end justify-between gap-2.5 pt-6 pb-2 px-4 border-b border-slate-100 dark:border-zinc-800">
              {dailyGenData.map((d: any, i: number) => {
                const pct = (d.value / maxGenValue) * 100;
                return (
                  <div key={i} className="flex-1 flex flex-col items-center gap-2 group h-full justify-end">
                    <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity">
                      {d.value}
                    </span>
                    <div 
                      className="w-full bg-indigo-600/10 hover:bg-indigo-600 dark:bg-indigo-500/10 dark:hover:bg-indigo-500 rounded-t-md transition-all duration-350 cursor-pointer"
                      style={{ height: `${pct * 0.75}%` }}
                    />
                    <span className="text-[10px] font-bold text-slate-500 dark:text-zinc-400">
                      {d.label}
                    </span>
                  </div>
                );
              })}
            </div>
            <div className="mt-4 flex items-center justify-between text-xs text-slate-500 dark:text-zinc-400 font-medium px-2">
              <span className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded bg-indigo-600" />
                Report compilations
              </span>
              <span>Average: {(dailyGenData.reduce((acc: number, val: any) => acc + val.value, 0) / dailyGenData.length).toFixed(1)} / day</span>
            </div>
          </CardContent>
        </Card>

        {/* User Growth Curve (SVG Smooth Bezier Line) */}
        {user?.role === 'Admin' && chartsData?.user_growth && chartsData.user_growth.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>User Platform Growth</CardTitle>
              <CardDescription>Visual tracker of cumulative user seats.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-48 w-full relative pt-6 pb-2 border-b border-slate-100 dark:border-zinc-800">
                {/* Custom SVG Line drawing */}
                <svg className="w-full h-full overflow-visible" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#6366f1" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="#6366f1" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>
                  {/* Area path */}
                  <path
                    d="M 10 120 Q 80 100, 160 85 T 320 60 T 480 35 L 480 150 L 10 150 Z"
                    fill="url(#chartGradient)"
                    className="w-full"
                  />
                  {/* Line Path */}
                  <path
                    d="M 10 120 Q 80 100, 160 85 T 320 60 T 480 35"
                    fill="none"
                    stroke="#6366f1"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    className="w-full"
                  />
                  {/* Circles for points */}
                  <circle cx="10" cy="120" r="4" fill="#6366f1" />
                  <circle cx="160" cy="85" r="4" fill="#6366f1" />
                  <circle cx="320" cy="60" r="4" fill="#6366f1" />
                  <circle cx="480" cy="35" r="4" fill="#6366f1" />
                </svg>
                {/* Bottom markers */}
                <div className="absolute bottom-1 inset-x-0 flex justify-between px-3 text-[10px] font-bold text-slate-500 dark:text-zinc-400">
                  {chartsData.user_growth.map((pt: any, idx: number) => (
                    <span key={idx}>{pt.label}</span>
                  ))}
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between text-xs text-slate-500 dark:text-zinc-400 font-medium px-2">
                <span className="flex items-center gap-1.5">
                  <span className="h-2.5 w-2.5 rounded-full border-2 border-indigo-650" />
                  Active platform accounts
                </span>
                <span>Trend: +250% Growth</span>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Quick Actions, Recent Users, & Activity Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions Panel */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Quick System Actions</CardTitle>
            <CardDescription>Shortcut shortcuts for operational tasks.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Button 
              variant="outline" 
              className="w-full justify-start text-xs font-semibold"
              onClick={() => navigate('/generator')}
            >
              <Cpu className="h-4 w-4 text-slate-400" />
              <span>Launch Document Generator</span>
            </Button>

            <Button 
              variant="outline" 
              className="w-full justify-start text-xs font-semibold"
              onClick={() => navigate('/history')}
            >
              <Layers className="h-4 w-4 text-slate-400" />
              <span>View Generated Audits</span>
            </Button>
          </CardContent>
        </Card>

        {/* Recent Registered Users Panel (Admin Only) */}
        {user?.role === 'Admin' && (
          <Card className="lg:col-span-1">
            <CardHeader className="flex flex-row justify-between items-center">
              <div>
                <CardTitle>Recent Registered Users</CardTitle>
                <CardDescription>Latest user sign-ups on the platform.</CardDescription>
              </div>
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => navigate('/users')}
                className="text-xs font-semibold flex items-center gap-1 animate-pulse hover:animate-none"
              >
                <span>View All</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-slate-100 dark:divide-zinc-800 max-h-[300px] overflow-y-auto">
                {recentUsers.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500 dark:text-zinc-400 font-medium">
                    No recent users found
                  </div>
                ) : (
                  recentUsers.map((u, index) => (
                    <div key={u.id || index} className="px-5 py-3.5 flex items-center gap-3 hover:bg-slate-50/50 dark:hover:bg-zinc-800/40 transition-colors">
                      <div className="h-8 w-8 rounded-full bg-indigo-100/30 dark:bg-indigo-500/10 flex items-center justify-center text-xs font-bold text-indigo-650 dark:text-indigo-400 flex-shrink-0">
                        {u.name.split(' ').map((n: string) => n[0]).join('').substring(0, 2).toUpperCase()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-slate-800 dark:text-zinc-300 truncate leading-tight">
                          {u.name}
                        </p>
                        <div className="flex items-center gap-1.5 mt-1 text-[10px] text-slate-450 dark:text-zinc-400 font-semibold truncate">
                          <Mail className="h-3.5 w-3.5 flex-shrink-0 text-slate-400" />
                          <span className="truncate">{u.email}</span>
                        </div>
                        <div className="flex items-center gap-1.5 mt-0.5 text-[9px] text-slate-450 dark:text-zinc-500 font-semibold font-mono">
                          <Clock className="h-3 w-3 flex-shrink-0 text-slate-400" />
                          <span>Joined {new Date(u.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <div>
                        <Badge 
                          variant={u.status === 'Active' ? 'success' : 'neutral'} 
                          className="text-[9px] scale-95 origin-right"
                        >
                          {u.status}
                        </Badge>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Recent Activity Audit Feed */}
        <Card className={user?.role === 'Admin' ? 'lg:col-span-1' : 'lg:col-span-2'}>
          <CardHeader className="flex flex-row justify-between items-center">
            <div>
              <CardTitle>Security & Operations Log</CardTitle>
              <CardDescription>Recent audit logs recorded by the platform engine.</CardDescription>
            </div>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => navigate('/history')}
              className="text-xs font-semibold flex items-center gap-1"
            >
              <span>View Audit Vault</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-slate-100 dark:divide-zinc-800 max-h-[300px] overflow-y-auto">
              {activities.map((act, index) => (
                <div key={index} className="px-5 py-3.5 flex items-start gap-3 hover:bg-slate-50/50 dark:hover:bg-zinc-800/40 transition-colors">
                  <div className="mt-0.5">
                    <Activity className="h-4 w-4 text-slate-450 dark:text-zinc-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-slate-800 dark:text-zinc-300 leading-tight">
                      {act.details}
                    </p>
                    <div className="flex items-center gap-2 mt-1.5 text-[10px] text-slate-400 dark:text-zinc-500 font-semibold">
                      <span>By {act.userName}</span>
                      <span>•</span>
                      <span>{new Date(act.timestamp).toLocaleTimeString()}</span>
                      <span>•</span>
                      <Badge variant="neutral" className="text-[9px] scale-95 origin-left">
                        {act.action}
                      </Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>


    </div>
  );
};
export default DashboardPage;
