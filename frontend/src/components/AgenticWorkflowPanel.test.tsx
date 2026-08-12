import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import AgenticWorkflowPanel from './AgenticWorkflowPanel'
import type { AgenticWorkflow } from '../api'

const workflow: AgenticWorkflow = {
  id: 'wf-1', document_id: 'doc-1', process_map_version_id: 'pm-2',
  process_map_version_label: 'v2', generator_version: 'manual-agent-pass-v1', status: 'draft',
  nodes: [
    {
      id: 'n1', node_kind: 'agent_escalation', title: 'Classify applicable cover',
      goal: 'Determine which cover applies', source_task_title: 'Classify which specific cover applies',
      spec: {
        grounding: { fabrication_check: 'x', misapplication_check: 'y' },
        confidence_escalation_trigger: { threshold_set_id: 'PROVISIONAL-v1-uncalibrated', calibration_owner: 'unassigned' },
      },
      citations: [
        { claim_id: 'c1', claim_type: 'rule', subject: 'accidental_damage_cover', modality: 'covers', statement: 's', raw_quote: 'q', page: 26, section_path: null, extraction_confidence: 0.9, extractor_version: 'manual-agent-pass-v1' },
      ],
    },
    {
      id: 'n2', node_kind: 'gateway', title: 'Outcome gateway', goal: 'Route by cause',
      source_task_title: null, spec: { grounding: { applicable: false, reason: 'routing only' } }, citations: [],
    },
  ],
  edges: [{ id: 'e1', from_node_id: 'n1', to_node_id: 'n2', condition_label: 'agent-judgment adverse' }],
}

describe('AgenticWorkflowPanel', () => {
  it('shows an empty state when no workflow exists', () => {
    render(<AgenticWorkflowPanel workflow={null} />)
    expect(screen.getByText(/no agentic workflow generated yet/i)).toBeInTheDocument()
  })

  it('renders the graph with each node, and selects the first node by default', () => {
    render(<AgenticWorkflowPanel workflow={workflow} />)
    expect(screen.getByTestId('agentic-workflow-canvas')).toBeInTheDocument()
    expect(screen.getByTestId('agentic-graph-node-n1')).toBeInTheDocument()
    expect(screen.getByTestId('agentic-graph-node-n2')).toBeInTheDocument()
    // First node is auto-selected -> its detail should show in the side panel.
    expect(screen.getByTestId('agentic-node-detail-panel')).toBeInTheDocument()
    expect(screen.getAllByText('Classify applicable cover').length).toBeGreaterThan(0)
  })

  it('shows the kind summary counts in the header', () => {
    render(<AgenticWorkflowPanel workflow={workflow} />)
    expect(screen.getByText(/1 Agent \+ escalation/)).toBeInTheDocument()
    expect(screen.getByText(/1 Gateway/)).toBeInTheDocument()
  })

  it('switches the detail panel when a different node is clicked', () => {
    render(<AgenticWorkflowPanel workflow={workflow} />)
    fireEvent.click(screen.getByTestId('agentic-graph-node-n2'))
    // Detail panel now shows node 2's goal, not node 1's.
    expect(screen.getByText('Route by cause')).toBeInTheDocument()
  })

  it('shows the uncalibrated confidence threshold + owner for the selected agent_escalation node', () => {
    render(<AgenticWorkflowPanel workflow={workflow} />)
    expect(screen.getByText(/PROVISIONAL-v1-uncalibrated/)).toBeInTheDocument()
    expect(screen.getByText(/unassigned/)).toBeInTheDocument()
  })

  it('shows cited claim subjects for the selected node', () => {
    render(<AgenticWorkflowPanel workflow={workflow} />)
    expect(screen.getByText(/accidental_damage_cover/i)).toBeInTheDocument()
  })

  it('expands the raw spec JSON on click', () => {
    render(<AgenticWorkflowPanel workflow={workflow} />)
    expect(screen.queryByTestId('agentic-node-raw-spec')).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('View raw spec JSON'))
    expect(screen.getByTestId('agentic-node-raw-spec')).toBeInTheDocument()
    expect(screen.getByText(/fabrication_check/)).toBeInTheDocument()
  })
})
