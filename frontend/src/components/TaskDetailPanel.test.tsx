import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TaskDetailPanel from './TaskDetailPanel'
import type { ProcessTask } from '../api'

const task: ProcessTask = {
  id: 't1',
  node_type: 'exclusion_test',
  title: 'Check general exclusions',
  description: 'Screen the claim against the general exclusions.',
  position_x: 0,
  position_y: 0,
  citations: [
    {
      claim_id: 'c1',
      claim_type: 'exclusion',
      subject: 'reckless_driving',
      modality: 'excludes',
      statement: 'No cover for a reckless act.',
      raw_quote: 'any reckless act by you, or by the driver of your car',
      page: 21,
      section_path: 'Section 3',
      extraction_confidence: 0.9,
      extractor_version: 'manual-agent-pass-v1',
    },
  ],
}

describe('TaskDetailPanel', () => {
  it('shows a placeholder when no task is selected', () => {
    render(<TaskDetailPanel task={null} />)
    expect(screen.getByText(/select a task/i)).toBeInTheDocument()
  })

  it('renders the task title, description, and citation count', () => {
    render(<TaskDetailPanel task={task} />)
    expect(screen.getByText('Check general exclusions')).toBeInTheDocument()
    expect(screen.getByText(/screen the claim/i)).toBeInTheDocument()
    expect(screen.getByText(/citations \(1\)/i)).toBeInTheDocument()
  })

  it('citation detail (raw quote) is hidden until the citation is clicked, then appears', () => {
    render(<TaskDetailPanel task={task} />)

    // Red-before-green as a live assertion: the raw quote must NOT be visible
    // before interaction — this is what proves the toggle actually gates it,
    // rather than the text being present all along.
    expect(screen.queryByTestId('citation-detail-c1')).not.toBeInTheDocument()

    fireEvent.click(screen.getByTestId('citation-toggle-c1'))

    expect(screen.getByTestId('citation-detail-c1')).toBeInTheDocument()
    expect(screen.getByText(/any reckless act by you/i)).toBeInTheDocument()
    expect(screen.getByText(/page 21/i)).toBeInTheDocument()
  })

  it('collapses the citation again on a second click', () => {
    render(<TaskDetailPanel task={task} />)
    const toggle = screen.getByTestId('citation-toggle-c1')
    fireEvent.click(toggle)
    expect(screen.getByTestId('citation-detail-c1')).toBeInTheDocument()
    fireEvent.click(toggle)
    expect(screen.queryByTestId('citation-detail-c1')).not.toBeInTheDocument()
  })
})
