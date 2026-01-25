import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { caseAPI, documentAPI } from '../../utils/api';
import QuestionFlow from '../QuestionFlow/QuestionFlow';
import './NewCase.css';

function NewCase() {
  const [step, setStep] = useState('questionnaire'); // questionnaire, review, generating
  const [caseData, setCaseData] = useState(null);
  const [createdCase, setCreatedCase] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleQuestionFlowComplete = (data) => {
    setCaseData(data);
    setStep('review');
  };

  const handleCreateCase = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await caseAPI.create({
        initialText: caseData.text,
        language: caseData.language,
        entities: caseData.entities,
        issueType: mapIssueType(caseData.issueType),
        subCategory: caseData.issueType,
      });

      setCreatedCase(response.data);
      setStep('generating');
    } catch (err) {
      setError('Failed to create case. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const mapIssueType = (subCategory) => {
    // Map sub-categories to main issue types
    const policeComplaintTypes = ['theft', 'assault', 'harassment'];
    const civilSuitTypes = ['property_dispute', 'contract_dispute'];
    const govApplicationTypes = ['rti', 'welfare_benefit'];

    if (policeComplaintTypes.includes(subCategory)) return 'police_complaint';
    if (civilSuitTypes.includes(subCategory)) return 'civil_suit';
    if (govApplicationTypes.includes(subCategory)) return 'government_application';
    return 'general_complaint';
  };

  const handleGenerateDocument = async () => {
    setLoading(true);
    try {
      const response = await documentAPI.generate({
        englishText: caseData.text,
        localText: caseData.text,
      });

      // Create blob and download
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${createdCase.referenceNumber}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);

      // Navigate to dashboard after a short delay
      setTimeout(() => {
        navigate('/dashboard');
      }, 2000);
    } catch (err) {
      setError('Failed to generate document. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleBackToEdit = () => {
    setStep('questionnaire');
  };

  return (
    <div className="new-case">
      <div className="new-case-header">
        <button onClick={() => navigate('/dashboard')} className="btn-back">
          ← Back to Dashboard
        </button>
        <h1>Create New Legal Document Case</h1>
      </div>

      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      {step === 'questionnaire' && (
        <QuestionFlow onComplete={handleQuestionFlowComplete} />
      )}

      {step === 'review' && caseData && (
        <div className="review-section">
          <div className="review-card">
            <h2>Review Your Information</h2>
            <p className="review-subtitle">
              Please verify all details before creating the case
            </p>

            <div className="review-grid">
              <div className="review-item">
                <span className="review-label">Issue Type:</span>
                <span className="review-value">{caseData.issueType?.replace('_', ' ')}</span>
              </div>

              <div className="review-item">
                <span className="review-label">Language:</span>
                <span className="review-value">{caseData.language}</span>
              </div>

              {Object.entries(caseData.entities || {}).map(([key, value]) => (
                value && (
                  <div key={key} className="review-item">
                    <span className="review-label">{key.replace('_', ' ')}:</span>
                    <span className="review-value">{value}</span>
                  </div>
                )
              ))}
            </div>

            <div className="review-description">
              <h3>Full Description:</h3>
              <p>{caseData.text}</p>
            </div>

            <div className="review-actions">
              <button onClick={handleBackToEdit} className="btn btn-secondary">
                Edit Information
              </button>
              <button
                onClick={handleCreateCase}
                className="btn btn-primary"
                disabled={loading}
              >
                {loading ? 'Creating Case...' : 'Confirm & Create Case'}
              </button>
            </div>
          </div>
        </div>
      )}

      {step === 'generating' && createdCase && (
        <div className="success-section">
          <div className="success-card">
            <div className="success-icon">✓</div>
            <h2>Case Created Successfully!</h2>
            <p className="success-ref">Reference Number: <strong>{createdCase.referenceNumber}</strong></p>

            <div className="case-summary">
              <p><strong>Issue Type:</strong> {createdCase.subCategory?.replace('_', ' ')}</p>
              <p><strong>Status:</strong> {createdCase.status}</p>
              {createdCase.suggestedAuthority && (
                <p><strong>Suggested Authority:</strong> {createdCase.suggestedAuthority}</p>
              )}
              <p><strong>Completeness:</strong> {Math.round((createdCase.completeness || 0) * 100)}%</p>
            </div>

            <div className="success-actions">
              <button
                onClick={handleGenerateDocument}
                className="btn btn-primary"
                disabled={loading}
              >
                {loading ? 'Generating PDF...' : '📄 Generate & Download PDF'}
              </button>
              <button onClick={() => navigate('/dashboard')} className="btn btn-secondary">
                Go to Dashboard
              </button>
            </div>

            <div className="disclaimer">
              ⚠️ <strong>DISCLAIMER:</strong> This is an auto-generated document for preliminary
              data collection only. It is NOT legal advice. Please have this document reviewed
              by a qualified legal professional before submission.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default NewCase;
