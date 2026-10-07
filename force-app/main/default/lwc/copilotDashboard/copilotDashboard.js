import { LightningElement, api, track } from 'lwc';
import { ShowToastEvent } from 'lightning/platformShowToastEvent';

export default class CopilotDashboard extends LightningElement {
    @api recordId;
    @track aiResponse = null;
    @track isLoading = false;
    @track errorMessage = null;

    async handleAnalyze() {
        this.isLoading = true;
        this.aiResponse = null;
        this.errorMessage = null;

        try {
            // Matches the exact POST route from main.py
            const response = await fetch(`http://localhost:8001/copilot/analyze/${this.recordId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                // 2. CRITICAL: Tells the browser to send the copilot_session cookie!
                credentials: 'include' 
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server Error ${response.status}: ${errorText}`);
            }

            this.aiResponse = await response.json();
            
        } catch (error) {
            this.errorMessage = error.message;
            console.error("Fetch Error:", error);
        } finally {
            this.isLoading = false;
        }
    }

    // Handles the "Approve & Save Draft" button click
    async handleExecuteAction(event) {
        const draftMessage = event.target.dataset.draft;
        this.isLoading = true;

        try {
            // 1. Prepare the exact Salesforce Task fields based on your ActionRequest schema
            const sfChanges = {
                WhatId: this.recordId,
                Subject: 'AI Drafted Outreach',
                Description: draftMessage,
                Status: 'Not Started',
                Priority: 'Normal',
                TaskSubtype: 'Email'
            };

            // 2. STEP 1: Propose the Action (Creates PENDING status)
            const proposeResponse = await fetch('http://localhost:8001/actions/propose', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({
                    action_type: 'CREATE',
                    target_object: 'Task',
                    proposed_changes: sfChanges
                })
            });
            
            if (!proposeResponse.ok) throw new Error('Failed to propose action');
            const proposal = await proposeResponse.json();
            const actionId = proposal.action_id; // Extract the generated UUID

            // 3. STEP 2: Approve the Action (Moves status to APPROVED)
            const approveResponse = await fetch(`http://localhost:8001/actions/${actionId}/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            
            if (!approveResponse.ok) throw new Error('Failed to approve action');

            // 4. STEP 3: Execute the Action (Writes to Salesforce & creates Audit Log)
            const executeResponse = await fetch(`http://localhost:8001/actions/${actionId}/execute`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });

            if (!executeResponse.ok) {
                const errorText = await executeResponse.text();
                throw new Error(`Execution Failed: ${errorText}`);
            }

            // Show a green success banner inside Salesforce
            this.dispatchEvent(
                new ShowToastEvent({
                    title: 'Action Approved & Executed!',
                    message: 'Draft email successfully saved as a Task in Salesforce.',
                    variant: 'success'
                })
            );

        } catch (error) {
            console.error("Execute Action Error:", error);
            this.dispatchEvent(
                new ShowToastEvent({
                    title: 'Execution Failed',
                    message: error.message,
                    variant: 'error'
                })
            );
        } finally {
            this.isLoading = false;
        }
    }
}