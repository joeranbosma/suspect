import numpy


class MRSData(numpy.ndarray):
    """
    numpy.ndarray subclass with additional metadata like sampling rate and echo
    time.
    """

    def __new__(cls, input_array, dt, f0, te=30, ppm0=4.7, voxel_dimensions=(10, 10, 10), transform=None, metadata=None):
        # Input array is an already formed ndarray instance
        # We first cast to be our class type
        obj = numpy.asarray(input_array).view(cls)
        # add the new attributes to the created instance
        obj.dt = dt
        obj.f0 = f0
        obj.te = te
        obj.ppm0 = ppm0
        obj.np = obj.shape[-1]
        obj.df = 1.0 / dt / obj.np
        obj.sw = 1.0 / dt
        obj.voxel_dimensions = voxel_dimensions
        obj.transform = transform
        obj.metadata = metadata
        return obj

    def __array_finalize__(self, obj):
        # if this instance is being created by slicing from another MRSData, copy the parameters across
        self.dt = getattr(obj, 'dt', None)
        self.f0 = getattr(obj, 'f0', None)
        self.te = getattr(obj, 'te', 30)
        self.ppm0 = getattr(obj, 'ppm0', None)
        self.np = self.shape[-1]

        # can only calculate these parameters if we have self.dt
        # if we don't have self.dt, this means this array is being created
        # with new and these will be calculated later
        if self.dt:
            self.df = 1.0 / self.dt / self.np
            self.sw = 1.0 / self.dt
        self.transform = getattr(obj, 'transform', None)
        self.metadata = getattr(obj, 'metadata', None)
        self.voxel_dimensions = getattr(obj, 'voxel_dimensions', (10, 10, 10))

    def __array_wrap__(self, obj):
        if len(obj.shape) == 0:
            return obj[()]
        else:
            return numpy.ndarray.__array_wrap__(self, obj)

    def __str__(self):
        return "<MRSData instance f0={0}MHz TE={1}ms dt={2}ms>".format(self.f0, self.te, self.dt * 1e3)

    def inherit(self, new_array):
        """
        Converts a generic numpy ndarray into an MRSData instance by copying
        its own MRS specific parameters. This is useful when performing some
        processing on the MRSData object gives a bare NDArray result.

        :param new_array: the ndarray to be converted to MRSData
        :return: a new MRSData instance with data from new_array and parameters from self.
        """
        cast_array = new_array.view(MRSData)
        cast_array.dt = self.dt
        cast_array.f0 = self.f0
        cast_array.np = self.np
        cast_array.df = self.df
        cast_array.te = self.te
        cast_array.ppm0 = self.ppm0
        cast_array.sw = self.sw
        cast_array.voxel_dimensions = self.voxel_dimensions
        cast_array.transform = self.transform
        cast_array.metadata = self.metadata
        return cast_array

    def spectrum(self):
        """
        Returns the Fourier transformed and shifted data

        :return:
        """
        return numpy.fft.fftshift(numpy.fft.fft(self, axis=-1), axes=-1)

    def hertz_to_ppm(self, frequency):
        """
        Converts a frequency in Hertz to the corresponding PPM for this dataset.

        :param frequency: the frequency in Hz
        :return:
        """
        return self.ppm0 - frequency / self.f0

    def ppm_to_hertz(self, frequency):
        """
        Converts a frequency in PPM to the corresponding Hertz for this dataset.

        :param frequency: the frequency in PPM
        :return:
        """
        return (self.ppm0 - frequency) * self.f0

    def time_axis(self):
        """
        Returns an array of the sample times in seconds for each point in the
        FID.

        :return: an array of the sample times in seconds for each point in the FID.
        """
        return numpy.arange(0.0, self.dt * self.np, self.dt)

    def frequency_axis(self):
        """
        Returns an array of frequencies in Hertz ranging from -sw/2 to
        sw/2.

        :return: an array of frequencies in Hertz ranging from -sw/2 to sw/2.
        """
        return numpy.linspace(-self.sw / 2, self.sw / 2, self.np, endpoint=False)

    def frequency_axis_ppm(self):
        """
        Returns an array of frequencies in PPM.

        :return:
        """
        return numpy.linspace(self.hertz_to_ppm(-self.sw / 2.0),
                       self.hertz_to_ppm(self.sw / 2.0),
                       self.np, endpoint=False)

    def voxel_size(self):
        """
        Returns the size of the voxel in mm^3.

        :return: the size of the voxel in mm^3.
        """
        return numpy.prod(self.voxel_dimensions)

    def to_scanner(self, x, y, z):
        """
        Converts a 3d position in MRSData space to the scanner reference frame

        :param x:
        :param y:
        :param z:
        :return:
        """
        if self.transform is None:
            raise ValueError("No transform set for MRSData object {}".format(self))

        transformed_point = self.transform * numpy.matrix([x, y, z, 1]).T

        return numpy.squeeze(numpy.asarray(transformed_point))[0:3]

    def from_scanner(self, x, y, z):
        """
        Converts a 3d position in the scanner reference frame to the MRSData space

        :param x:
        :param y:
        :param z:
        :return:
        """
        if self.transform is None:
            raise ValueError("No transform set for MRSData object {}".format(self))

        transformed_point = numpy.linalg.inv(self.transform) * numpy.matrix([x, y, z, 1]).T

        return numpy.squeeze(numpy.asarray(transformed_point))[0:3]