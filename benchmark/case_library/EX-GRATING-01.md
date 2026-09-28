# Check a grating order before moving a camera

For a transmission grating illuminated at normal incidence, use
`m * wavelength = pitch * sin(theta)` to check whether a proposed diffraction
order is physically possible. With a 1.5 micrometer pitch and 532 nm light,
the third order would require `sin(theta) = 1.064`, so it cannot propagate.
This check prevents a futile camera search.
