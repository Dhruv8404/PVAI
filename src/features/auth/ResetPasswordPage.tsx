import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '../../lib/resolver';
import * as z from 'zod';
import { useNavigate, Link } from 'react-router-dom';
import { ShieldCheck, ArrowLeft, Eye, EyeOff } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Card, CardContent } from '../../components/ui/Card';
import { useToast } from '../../components/ui/Toast';

const resetSchema = z.object({
  password: z.string().min(6, 'Password must be at least 6 characters'),
  confirmPassword: z.string().min(6, 'Please confirm your password')
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ['confirmPassword']
});

type ResetForm = z.infer<typeof resetSchema>;

export const ResetPasswordPage: React.FC = () => {
  const { toast } = useToast();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);


  const { register, handleSubmit, formState: { errors } } = useForm<ResetForm>({
    resolver: zodResolver(resetSchema)
  });

  const onSubmit = async () => {
    setSubmitting(true);
    await new Promise(resolve => setTimeout(resolve, 1000));
    setSubmitting(false);
    toast.success('Your password has been successfully reset.', 'Password Updated');
    navigate('/login');
  };

  return (
    <div className="w-full max-w-md mx-auto px-4">
      <div className="text-center mb-8">
        <div className="inline-flex p-2.5 rounded-2xl bg-indigo-600 dark:bg-indigo-500 text-white shadow-md mb-3">
          <ShieldCheck className="h-7 w-7" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-zinc-50 tracking-tight">
          Reset Password
        </h2>
        <p className="text-xs text-slate-500 dark:text-zinc-400 mt-2 font-medium">
          Create a new secure password for your account.
        </p>
      </div>

      <Card>
        <CardContent className="p-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 dark:text-zinc-300 uppercase tracking-wider mb-1.5">
                New Password
              </label>
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
              Reset Password
            </Button>
          </form>

          <div className="mt-5 pt-4 border-t border-slate-100 dark:border-zinc-800 text-center">
            <Link 
              to="/login" 
              className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 dark:text-zinc-400 dark:hover:text-zinc-200 font-semibold transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Back to Login</span>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};
export default ResetPasswordPage;
