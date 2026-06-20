from jarvis_os.verifier.verification_models import VerificationInput, VerificationResult, VerificationStatus

class VerificationRules:
    """
    Deterministic rules for verifying execution results.
    """
    
    @staticmethod
    def apply_rules(verification_input: VerificationInput) -> VerificationResult:
        execution = verification_input.execution_result
        
        # Rule 1: If retries exceeded
        if execution.get('retries_exceeded', False):
            return VerificationResult(
                status=VerificationStatus.CANCEL,
                reason="Max retries exceeded."
            )
            
        # Rule 2: If required data missing
        if execution.get('missing_data', False):
            return VerificationResult(
                status=VerificationStatus.FAILURE,
                reason="Required data is missing."
            )
            
        # Rule 3: If dependencies unresolved
        if execution.get('unresolved_dependencies', False):
            return VerificationResult(
                status=VerificationStatus.RETRY,
                reason="Dependencies are unresolved."
            )
            
        # Rule 4: If timeout
        if execution.get('timeout', False):
            return VerificationResult(
                status=VerificationStatus.RETRY,
                reason="Operation timed out."
            )
            
        # Rule 5: If action completed
        if execution.get('completed', False):
            # Check if there are partial issues
            if execution.get('warnings'):
                return VerificationResult(
                    status=VerificationStatus.PARTIAL_SUCCESS,
                    reason="Action completed with warnings.",
                    feedback_data={"warnings": execution.get('warnings')}
                )
            else:
                return VerificationResult(
                    status=VerificationStatus.SUCCESS,
                    reason="Action completed successfully."
                )
                
        # Default fallback
        return VerificationResult(
            status=VerificationStatus.FAILURE,
            reason="Unknown execution state."
        )
