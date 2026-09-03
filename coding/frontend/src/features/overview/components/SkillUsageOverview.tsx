import { ArrowUpRight, Loader2, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import type { OverviewSkillRow } from "../../../app/capability-registry";
import { HarnessAvatar } from "../../../components/harness/HarnessAvatar";
import { ToggleSwitch } from "../../../components/ToggleSwitch";
import type { HarnessCell } from "../../skills/public";
import { useOverviewCopy } from "../i18n";

interface SkillUsageOverviewProps {
  rows: OverviewSkillRow[];
  loading: boolean;
  pendingKeys: ReadonlySet<string>;
  onToggle: (row: OverviewSkillRow, cell: HarnessCell) => void;
}

export function SkillUsageOverview({
  rows,
  loading,
  pendingKeys,
  onToggle,
}: SkillUsageOverviewProps) {
  const copy = useOverviewCopy();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "enabled" | "disabled">("all");
  const filteredRows = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    return rows.filter((row) => {
      const matchesQuery = !query || `${row.name} ${row.description}`.toLocaleLowerCase().includes(query);
      const enabledCount = row.harnessCells.filter((cell) => cell.state === "enabled").length;
      const matchesFilter = filter === "all"
        || (filter === "enabled" && enabledCount > 0)
        || (filter === "disabled" && enabledCount === 0);
      return matchesQuery && matchesFilter;
    });
  }, [filter, rows, search]);

  return (
    <section className="overview-skills" aria-labelledby="overview-skills-title">
      <div className="overview-section__head overview-section__head--spread">
        <div>
          <h2 id="overview-skills-title">{copy.sections.skillsInUse}</h2>
          <p>{copy.sections.skillsInUseDescription}</p>
        </div>
        {!loading ? <span className="overview-skills__count">{filteredRows.length} / {rows.length}</span> : null}
      </div>

      <div className="overview-toolbar" aria-label="Skill 列表工具栏">
        <label className="overview-search">
          <Search size={17} aria-hidden="true" />
          <span className="u-visually-hidden">{copy.sections.searchLabel}</span>
          <input
            type="search"
            value={search}
            placeholder={copy.sections.searchPlaceholder}
            aria-label={copy.sections.searchLabel}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <div className="overview-filter" role="group" aria-label="Skill 开启状态筛选">
          {([
            ["all", copy.sections.filterAll],
            ["enabled", copy.sections.filterEnabled],
            ["disabled", copy.sections.filterDisabled],
          ] as const).map(([value, label]) => (
            <button
              type="button"
              key={value}
              className="overview-filter__button"
              data-active={filter === value}
              aria-pressed={filter === value}
              onClick={() => setFilter(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {loading && rows.length === 0 ? (
        <div className="overview-skill-list" aria-hidden="true">
          <div className="overview-skill-card overview-skill-card--skeleton" />
          <div className="overview-skill-card overview-skill-card--skeleton" />
        </div>
      ) : filteredRows.length > 0 ? (
        <div className="overview-skill-list">
          {filteredRows.map((row) => (
            <SkillUsageCard
              key={row.skillRef}
              row={row}
              pendingKeys={pendingKeys}
              onToggle={onToggle}
            />
          ))}
        </div>
      ) : rows.length > 0 ? (
        <p className="overview-empty-note">{copy.sections.noMatchingSkills}</p>
      ) : (
        <p className="overview-empty-note">{copy.sections.noSkillsInUse}</p>
      )}
    </section>
  );
}

function SkillUsageCard({
  row,
  pendingKeys,
  onToggle,
}: Omit<SkillUsageOverviewProps, "rows" | "loading"> & { row: OverviewSkillRow }) {
  const usage = row.contextUsage;
  const percent = usage.usagePercent;
  const available = usage.usagePercent !== null;

  return (
    <article className="overview-skill-card">
      <Link
        className="overview-skill-card__summary"
        to={`/overview?skill=${encodeURIComponent(row.skillRef)}`}
        aria-label={`查看 ${row.name} 详情`}
      >
        <div className="overview-skill-card__title-row">
          <h3>{row.name}</h3>
          <span>查看详情 <ArrowUpRight size={14} aria-hidden="true" /></span>
        </div>
        <p className="overview-skill-card__description">
          {row.description || "暂无简介"}
        </p>
        <div className="overview-skill-card__usage" data-status={usage.status}>
          <ResourceMetric label="上下文占用率" value={formatPercent(percent)} />
          <div className="overview-skill-card__meter" aria-hidden="true">
            <span style={{ width: `${available ? Math.min(Math.max(percent ?? 0, 0), 100) : 0}%` }} />
          </div>
        </div>
      </Link>

      <div className="overview-skill-card__harnesses" aria-label={`${row.name} 的 AI 开发工具状态`}>
        {row.harnessCells.map((cell) => {
          const pending = pendingKeys.has(toggleKey(row.skillRef, cell.harness));
          const checked = cell.state === "enabled";
          return (
            <div className="overview-harness-toggle" key={cell.harness} data-enabled={checked}>
              <HarnessAvatar harness={cell.harness} label={cell.label} logoKey={cell.logoKey} />
              <div className="overview-harness-toggle__identity">
                <strong>{cell.label}</strong>
                <span>{checked ? "已开启" : "已关闭"}</span>
              </div>
              {pending ? <Loader2 className="overview-harness-toggle__spinner" size={14} aria-hidden="true" /> : null}
              <ToggleSwitch
                checked={checked}
                disabled={!cell.interactive || pending}
                label=""
                ariaLabel={`${checked ? "关闭" : "开启"} ${row.name} 在 ${cell.label} 中的使用`}
                onCheckedChange={() => onToggle(row, cell)}
              />
            </div>
          );
        })}
        {row.harnessCells.length === 0 ? (
          <span className="overview-harness-toggle__empty">没有已安装的 AI 开发工具</span>
        ) : null}
      </div>
    </article>
  );
}

function ResourceMetric({ label, value }: { label: string; value: string }) {
  return (
    <span className="overview-skill-card__metric">
      <small>{label}</small>
      <strong>{value}</strong>
    </span>
  );
}

function formatPercent(percent: number | null): string {
  return percent === null ? "无法估算" : `${percent.toFixed(2)}%`;
}

export function toggleKey(skillRef: string, harness: string): string {
  return `${skillRef}::${harness}`;
}
