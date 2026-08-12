import { useEffect, useMemo, useState } from 'react'
import type { AgenticNodeKind, AgenticWorkflow } from '../api'
import { AGENTIC_NODE_LABEL } from '../nodeStyles'
import AgenticWorkflowGraphView from './AgenticWorkflowGraphView'
import AgenticNodeDetailPanel from './AgenticNodeDetailPanel'

interface Props {
  workflow: AgenticWorkflow | null
}

/** Top-level container for the "Agentic workflow" tab — a BPMN-style graph
 * (AgenticWorkflowGraphView, mirroring ProcessMapView's layout/interaction
 * pattern) plus a click-through detail panel (AgenticNodeDetailPanel,
 * mirroring TaskDetailPanel), instead of the flat scrolling card list this
 * used to be. Selection state lives here rather than in App.tsx because
 * nothing outside this tab needs to know which agentic node is selected
 * (unlike selectedTaskId, which the process-map tab's App-level state does
 * need for cross-tab consistency). */
export default function AgenticWorkflowPanel({ workflow }: Props) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  useEffect(() => {
    setSelectedNodeId(workflow?.nodes[0]?.id ?? null)
  }, [workflow])

  const selectedNode = useMemo(
    () => workflow?.nodes.find((n) => n.id === selectedNodeId) ?? null,
    [workflow, selectedNodeId],
  )

  if (workflow === null) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-slate-400">
        No agentic workflow generated yet for this document.
      </div>
    )
  }

  const kindCounts = workflow.nodes.reduce<Record<string, number>>((acc, n) => {
    acc[n.node_kind] = (acc[n.node_kind] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="flex h-full w-full flex-col" data-testid="agentic-workflow-panel">
      <div className="shrink-0 border-b border-slate-100 bg-white px-6 py-2.5">
        <p className="text-xs text-slate-400">
          Generated from process map {workflow.process_map_version_label} ({workflow.generator_version}) —
          a builder-ready spec for automating this process, not a replacement for the process map.
        </p>
        <p className="mt-1 text-[11px] text-slate-400">
          {Object.entries(kindCounts)
            .map(([kind, count]) => `${count} ${AGENTIC_NODE_LABEL[kind as AgenticNodeKind] ?? kind}`)
            .join(' · ')}
        </p>
      </div>
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 border-r border-slate-200">
          <AgenticWorkflowGraphView
            workflow={workflow}
            selectedNodeId={selectedNodeId}
            onSelectNode={setSelectedNodeId}
          />
        </div>
        <aside className="w-96 shrink-0 border-l border-slate-100 bg-white">
          <AgenticNodeDetailPanel node={selectedNode} />
        </aside>
      </div>
    </div>
  )
}
