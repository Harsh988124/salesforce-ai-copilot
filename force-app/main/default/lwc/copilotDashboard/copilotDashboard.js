import { LightningElement, api, track } from 'lwc';

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
            // 1. Matches the exact POST route from main.py
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
}