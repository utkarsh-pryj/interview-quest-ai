import React from 'react';

export const SkillBadge = ({ skill, type = 'matched' }) => {
  const name = typeof skill === 'string' ? skill : skill.canonical_name;

  return (
    <span className={`badge ${type}`}>
      {name}
    </span>
  );
};
