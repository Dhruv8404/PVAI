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

const registerSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.string().min(1, 'Email is required').email('Please enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
  confirmPassword: z.string().min(6, 'Please confirm your password')
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword']
});

type RegisterForm = z.infer<typeof registerSchema>;

export const RegisterPage: React.FC = () => {
  const { register: signup } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [pwdValue, setPwdValue] = useState('');

  const { register, handleSubmit, formState: { errors } } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: '',
      email: '',
      password: '',
      confirmPassword: ''
    }
  });

  const getPasswordStrength = (pwd: string) => {
    if (!pwd) return { score: 0, label: 'None', color: 'bg-slate-200' };
    let score = 0;
    if (pwd.length >= 6) score += 1;
    if (/[a-zA-Z]/.test(pwd) && /[0-9]/.test(pwd)) score += 1;
    if (/[^a-zA-Z0-9]/.test(pwd)) score += 1;
    if (pwd.length >= 10) score += 1;

    switch (score) {
      case 1: return { score, label: 'Weak', color: 'bg-rose-500' };
      case 2: return { score, label: 'Fair', color: 'bg-amber-500' };
      case 3: return { score, label: 'Good', color: 'bg-indigo-500' };
      case 4: return { score, label: 'Strong', color: 'bg-emerald-500' };
      default: return { score: 0, label: 'Weak', color: 'bg-rose-500' };
    }
  };

  const strength = getPasswordStrength(pwdValue);

  const onSubmit = async (data: RegisterForm) => {
    setSubmitting(true);
    try {
      await signup(data.name, data.email, data.password);
      toast.success('Account created successfully.', 'Welcome to PV Portal!');
      navigate('/dashboard');
    } catch (err: any) {
      toast.error(err.message || 'Onboarding failed.', 'Registration Failed');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="w-full max-w-md mx-auto px-4">
      <div className="text-center mb-8">
        <div className="inline-flex p-2.5 rounded-2xl bg-indigo-600 dark:bg-indigo-500 text-white shadow-md mb-3">
          <ShieldCheck className="h-7 w-7" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-zinc-50 tracking-tight">
          Create corporate account
        </h2>
        <p className="text-xs text-slate-500 dark:text-zinc-400 mt-2 font-medium">
          Set up credentials to log into the Document Generator.
        </p>
      </div>

      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-zinc-300 uppercase tracking-wider mb-1.5">
                Full Name
              </label>
              <input
                type="text"
                placeholder="Sarah Connor"
                {...register('name')}
                className={`w-full text-xs px-3 py-2.5 rounded-lg border bg-slate-50/50 dark:bg-zinc-950/50 text-slate-900 dark:text-zinc-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all ${
                  errors.name ? 'border-rose-300 focus:ring-rose-500' : 'border-slate-200 dark:border-zinc-800'
                }`}
              />
              {errors.name && (
                <p className="text-[10px] text-rose-500 font-semibold mt-1">{errors.name.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-zinc-300 uppercase tracking-wider mb-1.5">
                Corporate Email
              </label>
              <input
                type="email"
                placeholder="sarah.c@company.com"
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
              <label className="block text-xs font-bold text-slate-700 dark:text-zinc-300 uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  {...register('password', {
                    onChange: (e) => setPwdValue(e.target.value)
                  })}
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
              
              {/* Password strength meter */}
              {pwdValue && (
                <div className="mt-2.5">
                  <div className="flex justify-between items-center text-[9px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wide mb-1">
                    <span>Password Strength:</span>
                    <span>{strength.label}</span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-300 ${strength.color}`} 
                      style={{ width: `${(strength.score / 4) * 100}%` }}
                    />
                  </div>
                </div>
              )}
              
              {errors.password && (
                <p className="text-[10px] text-rose-500 font-semibold mt-1">{errors.password.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-zinc-300 uppercase tracking-wider mb-1.5">
                Confirm Password
              </label>
              <input
                type="password"
                placeholder="••••••••"
                {...register('confirmPassword')}
                className={`w-full text-xs px-3 py-2.5 rounded-lg border bg-slate-50/50 dark:bg-zinc-950/50 text-slate-900 dark:text-zinc-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-all ${
                  errors.confirmPassword ? 'border-rose-300 focus:ring-rose-500' : 'border-slate-200 dark:border-zinc-800'
                }`}
              />
              {errors.confirmPassword && (
                <p className="text-[10px] text-rose-500 font-semibold mt-1">{errors.confirmPassword.message}</p>
              )}
            </div>

            <Button type="submit" className="w-full text-xs py-2.5 mt-2" isLoading={submitting}>
              Register Account
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="text-center mt-6">
        <p className="text-xs font-medium text-slate-500 dark:text-zinc-400">
          Already registered?{' '}
          <Link to="/login" className="text-indigo-600 dark:text-indigo-400 font-bold hover:underline">
            Login here
          </Link>
        </p>
      </div>
    </div>
  );
};
export default RegisterPage;
