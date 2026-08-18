import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, showDetails: false }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('Caught by ErrorBoundary:', error, info)
  }

  handleReload = () => {
    window.location.reload()
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="app-container">
          <div className="panel error-page">
            <span className="app-mark error-mark">ERROR</span>
            <h2>Something went wrong</h2>
            <p>
              The app hit an unexpected error. Your data in the database is unaffected — this only
              broke the current page. Reloading usually fixes it.
            </p>
            <div className="error-actions">
              <button onClick={this.handleReload}>Reload Page</button>
              <button className="secondary" onClick={() => this.setState((s) => ({ showDetails: !s.showDetails }))}>
                {this.state.showDetails ? 'Hide' : 'Show'} technical details
              </button>
            </div>
            {this.state.showDetails && (
              <pre className="error-details">{String(this.state.error?.stack || this.state.error)}</pre>
            )}
          </div>
        </div>
      )
    }
    return this.props.children
  }
}