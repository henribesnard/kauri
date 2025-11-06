import React from 'react';

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-white border-t border-gray-200 py-3 px-6">
      <div className="flex items-center justify-center">
        <p className="text-xs text-gray-500">
          © {currentYear} Kauri. Tous droits réservés.
        </p>
      </div>
    </footer>
  );
};

export default Footer;
