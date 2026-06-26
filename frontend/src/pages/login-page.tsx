import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { authApi, showApiError } from "@/lib/api";
import { authStorage } from "@/lib/auth-storage";
import { useAuth } from "@/context/auth-context";
import { loginSchema, type LoginForm } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function LoginPage() {
  const navigate = useNavigate();
  const { completeLogin } = useAuth();
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: (tokens) => {
      authStorage.setTokens(tokens.access_token, tokens.refresh_token);
      completeLogin();
      toast.success("Welcome back");
      navigate("/", { replace: true });
    },
    onError: (error) => showApiError(error, "Unable to sign in"),
  });

  const onSubmit = handleSubmit(async (values) => {
    setSubmitting(true);
    try {
      await loginMutation.mutateAsync(values);
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sign in to ConvHub</CardTitle>
        <CardDescription>Access your team workspace and conversations.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" autoComplete="email" {...register("email")} />
            {errors.email && <p className="text-sm text-[var(--color-destructive)]">{errors.email.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              {...register("password")}
            />
            {errors.password && (
              <p className="text-sm text-[var(--color-destructive)]">{errors.password.message}</p>
            )}
          </div>

          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? "Signing in..." : "Sign in"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-[var(--color-muted-foreground)]">
          Don&apos;t have an account?{" "}
          <Link to="/register" className="text-[var(--color-foreground)] underline-offset-4 hover:underline">
            Create one
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
