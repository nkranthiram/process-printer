import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import AgenticNodeDetailPanel from './AgenticNodeDetailPanel'
import type { AgenticWorkflowNode } from '../api'

const node: AgenticWorkflowNode = {
  id: 'n1',
  node_kind: 'agent_escalation',
  title: 'Classify applicable cover',
  goal: 'Determine which cover applies',
  source_task_title: 'Classify which specific cover applies',
  spec: {
    decision_logic: 'May finalize a recommendation only when confidence is high and unambiguous.',
    grounding: { fabrication_check: 'exists verbatim', misapplication_check: 'supports the claim made' },
    confidence_escalation_trigger: {
      threshold_set_id: 'PROVISIONAL-v1-uncalibrated',
      calibration_owner: 'unassigned',
      calibration_dataset_version: 'none-yet',
      revalidation_trigger: 'on model/prompt change',
    },
    inputs: { fields: ['incident_narrative'] },
    outputs: { fields: ['candidate_covers'] },
    downstream_edges: ['confident & unambiguous', 'low confidence / ambiguous'],
  },
  citations: [
    { claim_id: 'c1', claim_type: 'rule', subject: 'accidental_damage_cover', modality: 'covers', statement: 'Covers accidental damage', raw_quote: 'accidental damage is covered', page: 26, section_path: null, extraction_confidence: 0.9, extractor_version: 'manual-agent-pass-v1' },
  ],
}

describe('AgenticNodeDetailPanel', () => {
  it('shows a placeholder when no node is selected', () => {
    render(<AgenticNodeDetailPanel node={null} />)
    expect(screen.getByText(/select a node/i)).toBeInTheDocument()
  })

  it('shows the node title, source task, and goal', () => {
    render(<AgenticNodeDetailPanel node={node} />)
    expect(screen.getByText('Classify applicable cover')).toBeInTheDocument()
    expect(screen.getByText(/Classify which specific cover applies/)).toBeInTheDocument()
    expect(screen.getByText('Determine which cover applies')).toBeInTheDocument()
  })

  it('shows decision logic and both grounding checks', () => {
    render(<AgenticNodeDetailPanel node={node} />)
    expect(screen.getByText(/May finalize a recommendation/)).toBeInTheDocument()
    expect(screen.getByText(/exists verbatim/)).toBeInTheDocument()
    expect(screen.getByText(/supports the claim made/)).toBeInTheDocument()
  })

  it('shows calibration metadata for the escalation trigger, not a bare threshold', () => {
    render(<AgenticNodeDetailPanel node={node} />)
    expect(screen.getByText(/PROVISIONAL-v1-uncalibrated/)).toBeInTheDocument()
    expect(screen.getByText(/unassigned/)).toBeInTheDocument()
    expect(screen.getByText(/none-yet/)).toBeInTheDocument()
  })

  it('shows downstream edges and citations', () => {
    render(<AgenticNodeDetailPanel node={node} />)
    expect(screen.getByText('confident & unambiguous')).toBeInTheDocument()
    expect(screen.getByText(/Covers accidental damage/)).toBeInTheDocument()
  })

  it('handles a node with grounding not applicable', () => {
    const structural: AgenticWorkflowNode = {
      ...node,
      id: 'n2',
      node_kind: 'gateway',
      spec: { grounding: { applicable: false, reason: 'routing only' } },
      citations: [],
    }
    render(<AgenticNodeDetailPanel node={structural} />)
    expect(screen.getByText(/routing only/)).toBeInTheDocument()
    expect(screen.getByText(/no directly cited source text/i)).toBeInTheDocument()
  })
})
