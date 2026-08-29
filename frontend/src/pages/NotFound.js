import { Link } from "react-router-dom";
import { ShieldOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Wordmark } from "@/components/Brand";

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-background px-6 text-center">
      <Wordmark showTagline testId="notfound-wordmark" />
      <ShieldOff className="h-8 w-8 text-muted-foreground" />
      <div>
        <h1 className="font-display text-2xl font-semibold text-foreground">Nothing here</h1>
        <p className="mt-2 max-w-sm text-sm text-muted-foreground">
          Vexen defaults to deny — including for routes that do not exist.
        </p>
      </div>
      <div className="flex gap-2">
        <Button asChild variant="outline" data-testid="notfound-home">
          <Link to="/">Back to home</Link>
        </Button>
        <Button asChild data-testid="notfound-console">
          <Link to="/app">Open console</Link>
        </Button>
      </div>
    </div>
  );
}
