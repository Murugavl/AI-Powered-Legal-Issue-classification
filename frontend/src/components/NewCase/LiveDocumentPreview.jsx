import './CaseWizard.css';

function LiveDocumentPreview({ data, onEdit, onConfirm, loading }) {
    const { detectedIntent, extractedEntities } = data;
    const today = new Date().toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    });

    return (
        <div className="preview-container">
            <div className="preview-header">
                <h2>Document Preview</h2>
                <div className="preview-actions-top">
                    <button className="btn-text" onClick={onEdit}>✎ Edit Facts</button>
                </div>
            </div>

            <div className="document-paper">
                <div className="doc-content">
                    <h1 className="doc-title">{detectedIntent?.toUpperCase() || 'LEGAL DOCUMENT'}</h1>

                    <div className="doc-meta">
                        <p><strong>Date:</strong> {today}</p>
                    </div>

                    <div className="doc-body">
                        <p><strong>To:</strong></p>
                        <p className="placeholder-text">
                            [The Competent Authority / {extractedEntities?.accused || 'Recipient Name'}]<br />
                            {extractedEntities?.location || '[Address]'}
                        </p>

                        <p><strong>Subject:</strong> {detectedIntent} regarding {extractedEntities?.domain || 'legal issue'}.</p>

                        <p><strong>Sir/Madam,</strong></p>

                        <p>
                            I, <strong>{extractedEntities?.name || '[Your Name]'}</strong>, residing at {extractedEntities?.location || '[Location]'},
                            wish to bring the following facts to your attention:
                        </p>

                        <p>
                            That on <strong>{extractedEntities?.date || '[Date]'}</strong>, an incident occurred involving
                            {extractedEntities?.accused ? ` one ${extractedEntities.accused}` : ' certain parties'}.
                        </p>

                        {extractedEntities?.amount && (
                            <p>
                                This matter involves a financial sum of <strong>{extractedEntities.amount}</strong>.
                            </p>
                        )}

                        <p>
                            The details of the incident are as follows: <br />
                            {/* We would inject the full summary here if available, using the entities for now */}
                            It is stated that {extractedEntities?.relationship ? `my ${extractedEntities.relationship}` : 'the accused'}
                            has caused the issue described as "{extractedEntities?.issue_type || 'the incident'}" in the jurisdiction of {extractedEntities?.location}.
                        </p>

                        <p>
                            I request you to kindly take necessary legal action and provide justice.
                        </p>

                        <br />
                        <p>Yours Faithfully,</p>
                        <br />
                        <p>____________________</p>
                        <p><strong>{extractedEntities?.name}</strong></p>
                    </div>
                </div>
            </div>

            <div className="preview-footer">
                <p className="preview-disclaimer">
                    * This is a computer-generated draft. Please consult a lawyer before signing.
                </p>
                <div className="preview-buttons">
                    <button className="btn btn-secondary" onClick={onEdit}>
                        ← Continue Chatting
                    </button>
                    <button className="btn btn-primary" onClick={onConfirm} disabled={loading}>
                        {loading ? 'Generating Final PDF...' : '⬇ Download & Share'}
                    </button>
                </div>
            </div>
        </div>
    );
}

export default LiveDocumentPreview;
