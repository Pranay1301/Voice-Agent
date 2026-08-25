function parseCallbackTime(phrase, referenceDate = new Date(), timezone = 'Asia/Kolkata') {
  // A simplified mock implementation
  // In a real app, you might use chrono-node or a similar library
  
  const text = phrase.toLowerCase();
  const ref = new Date(referenceDate);
  
  let date = new Date(ref);
  let timeStr = '10:00:00';
  let isAmbiguous = false;
  let needsClarification = false;
  
  if (text.includes('tomorrow') || text.includes('kal')) {
    date.setDate(date.getDate() + 1);
    if (text.includes('morning') || text.includes('subah')) {
      timeStr = '10:00:00';
    } else if (text.includes('evening') || text.includes('shaam')) {
      timeStr = '18:00:00';
    } else {
      isAmbiguous = true;
      needsClarification = true;
    }
  } else if (text.includes('day after tomorrow') || text.includes('parso')) {
    date.setDate(date.getDate() + 2);
    timeStr = '10:00:00';
  } else if (text.includes('next monday')) {
    const daysUntilMonday = (1 + 7 - date.getDay()) % 7 || 7;
    date.setDate(date.getDate() + daysUntilMonday);
    timeStr = text.includes('evening') ? '18:00:00' : '10:00:00';
  } else if (text.includes('weekend pe')) {
    const daysUntilSaturday = (6 + 7 - date.getDay()) % 7 || 7;
    date.setDate(date.getDate() + daysUntilSaturday);
    timeStr = '10:00:00';
  } else if (text.includes('next week')) {
    const daysUntilMonday = (1 + 7 - date.getDay()) % 7 || 7;
    date.setDate(date.getDate() + daysUntilMonday);
    timeStr = '10:00:00';
  } else if (text.includes('after 6')) {
    const currentHour = ref.getHours();
    if (currentHour >= 18) {
      date.setDate(date.getDate() + 1);
    }
    timeStr = '18:00:00';
  } else if (text.includes('in an hour')) {
    date.setHours(date.getHours() + 1);
    timeStr = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}:00`;
  } else {
    isAmbiguous = true;
    needsClarification = true;
  }
  
  const dateStr = date.toISOString().split('T')[0];
  const isoString = `${dateStr}T${timeStr}.000Z`;
  
  return {
    date: dateStr,
    time: timeStr,
    isAmbiguous,
    needsClarification,
    structured: isoString
  };
}

module.exports = { parseCallbackTime };
