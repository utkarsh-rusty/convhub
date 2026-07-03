import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { authApi, demoApi, showApiError } from "@/lib/api";
import { APP_HOME } from "@/lib/site";
import { authStorage } from "@/lib/auth-storage";
import { useAuth } from "@/context/auth-context";
import { loginSchema, type DemoPersona, type LoginForm } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

export function LoginPage() {
  const navigate = useNavigate();
  const { completeLogin } = useAuth();
  const [submitting, setSubmitting] = useState(false);

  const { data: demoConfig } = useQuery({
    queryKey: ["demo-config"],
    queryFn: () => demoApi.getConfig(),
    staleTime: 60_000,
  });

  const { data: demoUsers } = useQuery({
    queryKey: ["demo-users"],
    queryFn: () => demoApi.listUsers(),
    enabled: Boolean(demoConfig?.enabled),
    staleTime: 60_000,
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const finishLogin = (
    accessToken: string,
    refreshToken: string,
    workspaceId?: string | null,
  ) => {
    authStorage.setTokens(accessToken, refreshToken);
    if (workspaceId) {
      authStorage.setWorkspaceId(workspaceId);
    }
    completeLogin();
    toast.success("Welcome back");
    navigate(APP_HOME, { replace: true });
  };

  const loginMutation = useMutation({
    mutationFn: authApi.login,
    onSuccess: (tokens) => {
      finishLogin(tokens.access_token, tokens.refresh_token);
    },
    onError: (error) => showApiError(error, "Unable to sign in"),
  });

  const demoLoginMutation = useMutation({
    mutationFn: (persona: DemoPersona) => demoApi.login(persona),
    onSuccess: (tokens) => {
      finishLogin(tokens.access_token, tokens.refresh_token, tokens.workspace_id);
    },
    onError: (error) => showApiError(error, "Unable to sign in as demo user"),
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
        <Link
          to="/"
          className="mb-2 inline-block text-xs uppercase tracking-[0.2em] text-[var(--color-muted-foreground)] transition-colors hover:text-[var(--color-foreground)]"
        >
          ConvHub
        </Link>
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

        {demoConfig?.enabled && demoUsers?.users.length ? (
          <>
            <Separator className="my-6" />
            <div className="space-y-3">
              <div>
                <p className="text-sm font-medium">Login as Demo User</p>
                <p className="text-xs text-[var(--color-muted-foreground)]">
                  Jump into the seeded demo workspace instantly.
                </p>
              </div>
              <div className="grid gap-2">
                {demoUsers.users.map((user) => (
                  <Button
                    key={user.persona}
                    type="button"
                    variant="secondary"
                    className="w-full justify-start"
                    disabled={demoLoginMutation.isPending}
                    onClick={() => demoLoginMutation.mutate(user.persona)}
                  >
                    {demoLoginMutation.isPending ? "Signing in..." : `Continue as ${user.name}`}
                  </Button>
                ))}
              </div>
            </div>
          </>
        ) : null}

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
