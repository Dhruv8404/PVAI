import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '../../lib/resolver';
import * as z from 'zod';
import { Link } from 'react-router-dom';
import { ShieldCheck, Mail, ArrowLeft } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Card, CardContent } from '../../components/ui/Card';
import { useToast } from '../../components/ui/Toast';

const forgotSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Please enter a valid email address'),
});

type ForgotForm = z.infer<typeof forgotSchema>;

export const ForgotPasswordPage: React.FC = () => {
  const { toast } = useToast();
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<ForgotForm>({
    resolver: zodResolver(forgotSchema)
  });

  const onSubmit = async () => {
    setSubmitting(true);
    await new Promise(resolve => setTimeout(resolve, 800));
    setSubmitting(false);
    setSubmitted(true);
    toast.success('Simulation recovery link dispatched.', 'Reset Link Sent');
  };

  return (
    <div className="w-full max-w-md mx-auto px-4">
      <div className="text-center mb-8">
        <div className="inline-flex p-2.5 rounded-2xl bg-indigo-600 dark:bg-indigo-500 text-white shadow-md mb-3">
          <ShieldCheck className="h-7 w-7" />
        </div>
        <h2 className="text-2xl font-bold text-slate-900 dark:text-zinc-50 tracking-tight">
          Forgot Password
        </h2>
        <p className="text-xs text-slate-500 dark:text-zinc-400 mt-2 font-medium">
          Retrieve access credentials for your account.
        </p>
      </div>

      <Card>
        <CardContent className="p-6">
          {!submitted ? (
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

              <Button type="submit" className="w-full text-xs py-2.5" isLoading={submitting}>
                Send Recovery Instructions
              </Button>
            </form>
          ) : (
            <div className="text-center py-4 space-y-4">
              <div className="inline-flex p-3 rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <Mail className="h-6 w-6" />
              </div>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-zinc-50">
                Recovery Link Dispatched
              </h3>
              <p className="text-xs text-slate-500 dark:text-zinc-400 leading-relaxed font-medium">
                We have generated a mock password reset sequence. In a production environment, an email verification webhook would be fired here.
              </p>
              
              <div className="pt-2">
                <Link to="/reset-password">
                  <Button variant="primary" size="sm" className="w-full text-xs">
                    Access Reset Portal Page (Demo)
                  </Button>
                </Link>
              </div>
            </div>
          )}

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
export default ForgotPasswordPage;
