import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import App from './App'
import * as api from './api'

const doc: api.DocumentSummary = {
  id: 'doc-1', filename: 'aami.pdf', title: 'AAMI Comprehensive Car Insurance PDS',
  page_count: 76, status: 'ready', uploaded_at: '2026-08-05T00:00:00Z',
}

const processMap: api.ProcessMap = {
  id: 'pm-1', document_id: 'doc-1', version_label: 'v1', status: 'draft',
  tasks: [
    { id: 't1', node_type: 'input_required', title: 'Capture the claim description', description: 'Record what happened.', position_x: 0, position_y: 0, citations: [] },
    { id: 't2', node_type: 'decision', title: 'Reach the coverage decision', description: 'Decide.', position_x: 0, position_y: 100, citations: [] },
  ],
  edges: [{ id: 'e1', from_task_id: 't1', to_task_id: 't2', condition_label: 'Always' }],
}

const issues: api.Issue[] = [
  { id: 'i1', issue_type: 'gap', title: 'A gap', description: 'desc', status: 'open', process_task_id: null, claim_refs: [] },
]

const validationCases: api.ValidationCase[] = [
  {
    id: 'v1', scenario_name: 'Windscreen chip', claim_description: 'desc',
    expected_outcome: 'Covered', actual_outcome: 'Covered',
    traced_path: ['t1', 't2'], result: 'pass', notes: null,
  },
]

afterEach(() => {
  vi.restoreAllMocks()
})

describe('App', () => {
  it('loads documents and process map, then renders the map tab with the header info', async () => {
    vi.spyOn(api, 'listDocuments').mockResolvedValue([doc])
    vi.spyOn(api, 'getProcessMap').mockResolvedValue(processMap)
    vi.spyOn(api, 'listIssues').mockResolvedValue(issues)
    vi.spyOn(api, 'listValidationCases').mockResolvedValue(validationCases)

    render(<App />)

    expect(screen.getByText(/loading process map/i)).toBeInTheDocument()

    await waitFor(() => expect(screen.getByText('AAMI Comprehensive Car Insurance PDS', { exact: false })).toBeInTheDocument())
    expect(screen.getByText(/76 pages/i)).toBeInTheDocument()
    expect(screen.getByTestId('process-map-canvas')).toBeInTheDocument()
    expect(screen.getByTestId('tab-issues')).toHaveTextContent('1')
  })

  it('switching to the issues tab shows the loaded issues, not the map', async () => {
    vi.spyOn(api, 'listDocuments').mockResolvedValue([doc])
    vi.spyOn(api, 'getProcessMap').mockResolvedValue(processMap)
    vi.spyOn(api, 'listIssues').mockResolvedValue(issues)
    vi.spyOn(api, 'listValidationCases').mockResolvedValue(validationCases)

    render(<App />)
    await waitFor(() => screen.getByTestId('tab-issues'))

    fireEvent.click(screen.getByTestId('tab-issues'))

    expect(screen.getByTestId('issues-panel')).toBeInTheDocument()
    expect(screen.queryByTestId('process-map-canvas')).not.toBeInTheDocument()
    expect(screen.getByText('A gap')).toBeInTheDocument()
  })

  it('switching to the chat tab renders the chat panel', async () => {
    vi.spyOn(api, 'listDocuments').mockResolvedValue([doc])
    vi.spyOn(api, 'getProcessMap').mockResolvedValue(processMap)
    vi.spyOn(api, 'listIssues').mockResolvedValue(issues)
    vi.spyOn(api, 'listValidationCases').mockResolvedValue(validationCases)

    render(<App />)
    await waitFor(() => screen.getByTestId('tab-chat'))
    fireEvent.click(screen.getByTestId('tab-chat'))

    expect(screen.getByTestId('chat-panel')).toBeInTheDocument()
  })

  it('shows an explicit error state if the API call fails, not a blank screen', async () => {
    vi.spyOn(api, 'listDocuments').mockRejectedValue(new Error('backend unreachable'))

    render(<App />)

    await waitFor(() => expect(screen.getByText(/couldn.t load process printer/i)).toBeInTheDocument())
    expect(screen.getByText(/backend unreachable/i)).toBeInTheDocument()
  })
})
