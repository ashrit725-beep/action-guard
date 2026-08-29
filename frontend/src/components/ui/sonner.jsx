import { Toaster as Sonner, toast } from "sonner";

import { useTheme } from "@/context/ThemeContext";

/**
 * Toasts follow Vexen's own theme toggle (not the operating system), so a light
 * toast can never land on top of the dark console.
 */
const Toaster = ({ ...props }) => {
  const { theme } = useTheme();

  return (
    <Sonner
      theme={theme === "dark" ? "dark" : "light"}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:bg-popover group-[.toaster]:text-popover-foreground group-[.toaster]:border-border group-[.toaster]:shadow-lg",
          description: "group-[.toast]:text-muted-foreground",
          actionButton: "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton: "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
          closeButton:
            "group-[.toast]:border-border group-[.toast]:bg-popover group-[.toast]:text-muted-foreground",
          success: "group-[.toaster]:border-[hsl(var(--status-allow)/0.4)]",
          error: "group-[.toaster]:border-[hsl(var(--status-block)/0.45)]",
          warning: "group-[.toaster]:border-[hsl(var(--status-approval)/0.45)]",
        },
      }}
      {...props}
    />
  );
};

export { Toaster, toast };
