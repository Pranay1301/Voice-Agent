const router = require('express').Router();
const database = require('../config/database');

// GET /api/leads
router.get('/', (req, res) => {
  const leads = database.getLeads(50);
  res.json(leads);
});

// GET /api/leads/:id
router.get('/:id', (req, res) => {
  const lead = database.getLead(req.params.id);
  if (!lead) {
    return res.status(404).json({ error: 'Lead not found' });
  }
  res.json(lead);
});

module.exports = router;
