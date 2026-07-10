import Link from "next/link";

export default function VerifyRequestPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="text-center max-w-md">
        <h1 className="text-2xl font-semibold mb-2">Check your email</h1>
        <p className="text-muted-foreground mb-4">
          A sign-in link has been sent. In development, check the server console for the URL.
        </p>
        <Link href="/login" className="text-accent hover:underline text-sm">
          Back to login
        </Link>
      </div>
    </div>
  );
}
