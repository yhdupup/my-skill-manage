import { useId, type SVGProps } from "react";

import { cn } from "../../lib/utils";

interface DotPatternProps extends SVGProps<SVGSVGElement> {
  width?: string | number;
  height?: string | number;
  x?: string | number;
  y?: string | number;
  cx?: string | number;
  cy?: string | number;
  cr?: string | number;
}

export function DotPattern({
  width = 16,
  height = 16,
  x = 0,
  y = 0,
  cx = 1,
  cy = 1,
  cr = 1,
  className,
  ...props
}: DotPatternProps) {
  const id = useId();

  return (
    <svg
      aria-hidden="true"
      className={cn("dot-pattern", className)}
      focusable="false"
      {...props}
    >
      <defs>
        <pattern
          id={id}
          width={width}
          height={height}
          patternUnits="userSpaceOnUse"
          patternContentUnits="userSpaceOnUse"
          x={x}
          y={y}
        >
          <circle cx={cx} cy={cy} r={cr} />
        </pattern>
      </defs>
      <rect width="100%" height="100%" strokeWidth={0} fill={`url(#${id})`} />
    </svg>
  );
}
