import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '../../lib/resolver';
import * as z from 'zod';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldCheck, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/Button';
import { Card, CardContent } from '../../components/ui/Card';
import { useToast } from '../../components/ui/Toast';

const loginSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  rememberMe: z.boolean().optional()
});

type LoginForm = z.infer<typeof loginSchema>;

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
      rememberMe: false
    }
  });

  const onSubmit = async (data: LoginForm) => {
    setSubmitting(true);
    try {
      await login(data.email, data.password);
      toast.success('Access granted.', 'Welcome back!');
      navigate('/dashboard');
    } catch (err: any) {
      toast.error(err.message || 'Verification failed. Try again.', 'Login Failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto px-4">
      {/* Brand logo & title */}
      <div className="text-center mb-8">
        <div className="inline-flex p-2.5 rounded-2xl bg-indigo-600 dark:bg-indigo-500 text-white shadow-md mb-3">
          <ShieldCheck className="h-7 w-7" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-zinc-50 tracking-tight">
          Sign in to PV Portal
        </h2>
        <p className="text-xs text-slate-500 dark:text-zinc-400 mt-2 font-medium">
          Enter credentials or sign up for a new account.
        </p>
      </div>

      {/* Main card form */}
      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-zinc-300 uppercase tracking-wider mb-1.5">
                Corporate Email
              </label>
              <input
                type="email"
                placeholder="you@company.com"
                {...register('email')}
                className={`w-full text-xs px-3 py-2.5 rounded-lg border bg-slate-50/50 dark:bg-zinc-950/50 text-slate-900 dark:text-zinc-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all ${
                  errors.email ? 'border-rose-300 focus:ring-rose-500' : 'border-slate-200 dark:border-zinc-800'
                }`}
              />
              {errors.email && (
                <p className="text-[10px] text-rose-500 font-semibold mt-1">{errors.email.message}</p>
              )}
            </div>

            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label className="block text-xs font-bold text-slate-700 dark:text-zinc-300 uppercase tracking-wider">
                  Password
                </label>
                <Link 
                  to="/forgot-password" 
                  className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold hover:underline"
                >
                  Forgot?
                </Link>
              </div>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  {...register('password')}
                  className={`w-full text-xs px-3 py-2.5 rounded-lg border bg-slate-50/50 dark:bg-zinc-950/50 text-slate-900 dark:text-zinc-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all pr-10 ${
                    errors.password ? 'border-rose-300 focus:ring-rose-500' : 'border-slate-200 dark:border-zinc-800'
                  }`}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-2.5 text-slate-400 hover:text-slate-500 dark:hover:text-zinc-300"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-[10px] text-rose-500 font-semibold mt-1">{errors.password.message}</p>
              )}
            </div>

            <div className="flex items-center justify-between py-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  {...register('rememberMe')}
                  className="h-4 w-4 rounded border-slate-300 dark:border-zinc-700 text-indigo-600 focus:ring-indigo-500 dark:bg-zinc-950"
                />
                <span className="text-xs font-semibold text-slate-600 dark:text-zinc-400">Remember session</span>
              </label>
            </div>

            <Button type="submit" className="w-full text-xs py-2.5 mt-2" isLoading={submitting}>
              Access Platform
            </Button>
          </form>

          {/* Quick seeded logins shortcut helper */}
          <div className="mt-5 pt-4 border-t border-slate-100 dark:border-zinc-800 text-left">
            <span className="text-[10px] font-bold text-slate-400 dark:text-zinc-500 uppercase tracking-wider block mb-2">Quick Access Demo Accounts</span>
            <div className="grid grid-cols-2 gap-2 text-[10px] font-semibold">
              <div className="p-2 bg-slate-50 dark:bg-zinc-850 border border-slate-150 dark:border-zinc-800 rounded">
                <span className="text-slate-500 block">Admin role:</span>
                <span className="text-slate-900 dark:text-zinc-200">admin@company.com</span>
                <span className="text-slate-400 block mt-0.5">Password123!</span>
              </div>
              <div className="p-2 bg-slate-50 dark:bg-zinc-850 border border-slate-150 dark:border-zinc-800 rounded">
                <span className="text-slate-500 block">User role:</span>
                <span className="text-slate-900 dark:text-zinc-200">user@company.com</span>
                <span className="text-slate-400 block mt-0.5">Password123!</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="text-center mt-6">
        <p className="text-xs font-medium text-slate-500 dark:text-zinc-400">
          New here?{' '}
          <Link to="/register" className="text-indigo-600 dark:text-indigo-400 font-bold hover:underline">
            Create an Account
          </Link>
        </p>
      </div>
    </div>
  );
};
export default LoginPage;
