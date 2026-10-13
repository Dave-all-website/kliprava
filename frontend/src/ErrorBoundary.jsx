import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Kliprava Uncaught Render Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#080B14] text-slate-100 flex items-center justify-center p-4">
          <div className="max-w-md w-full p-6 rounded-2xl bg-slate-900/90 border border-rose-500/30 text-center shadow-2xl backdrop-blur-xl space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-rose-500/20 text-rose-400 mx-auto flex items-center justify-center">
              <AlertCircle size={28} />
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-100 font-display">Tampilan Mengalami Kendala</h2>
              <p className="text-xs text-slate-400 font-mono mt-1">
                {this.state.error?.message || 'Terjadi kesalahan sistem saat merender antarmuka.'}
              </p>
            </div>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-rose-500 to-purple-600 text-white text-xs font-bold shadow-lg shadow-rose-500/25 hover:scale-105 transition cursor-pointer"
            >
              <RefreshCw size={14} /> Pulihkan & Muat Ulang
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
