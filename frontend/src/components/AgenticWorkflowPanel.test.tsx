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
  edges: [{ id: 'e1', from_node_id: 'n1', to_node_id: 'n2', condition_label: 'confident' }],
}

describe('AgenticWorkflowPanel', () => {
  it('shows an empty state when no workflow exists', () => {
    render(<AgenticWorkflowPanel workflow={null} />)
    expect(screen.getByText(/no agentic workflow generated yet/i)).toBeInTheDocument()
  })

  it('renders each node with its kind badge and goal', () => {
    render(<AgenticWorkflowPanel workflow={workflow} />)
    expect(screen.getByText('Classify applicable cover')).toBeInTheDocument()
    expect(screen.getByText('Determine which cover applies')).toBeInTheDocument()
    expect(screen.getByText('Outcome gateway')).toBeInTheDocument()
    expect(screen.getByText(/from: Classify which specific cover applies/)).toBeInTheDocument()
  })

  it('shows the uncalibrated confidence threshold + owner for an agent_escalation node', () => {
    render(<AgenticWorkflowPanel workflow={workflow} />)
    expect(screen.getByText(/PROVISIONAL-v1-uncalibrated/)).toBeInTheDocument()
    expect(screen.getByText(/unassigned/)).toBeInTheDocument()
  })

  it('shows cited claim subjects', () => {
    render(<AgenticWorkflowPanel workflow={workflow} />)
    expect(screen.getByText(/accidental_damage_cover/)).toBeInTheDocument()
  })

  it('expands the full spec JSON on "View spec" click', () => {
    render(<AgenticWorkflowPanel workflow={workflow} />)
    expect(screen.queryAllByTestId('agentic-node-spec')).toHaveLength(0)

    fireEvent.click(screen.getAllByText('View spec')[0])

    expect(screen.getAllByTestId('agentic-node-spec')).toHaveLength(1)
    expect(screen.getByText(/fabrication_check/)).toBeInTheDocument()
  })
})
