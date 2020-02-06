package quic

import (
	. "github.com/onsi/ginkgo"
	. "github.com/onsi/gomega"
)

var _ = Describe("StreamToPath", func() {
	var (
		streamToPath StreamToPath
	)
	Context("", func() {
		BeforeEach(func() {
			streamToPath = StreamToPath{} // maps are reference types itself
			streamToPath.Add(1, 1)
			streamToPath.Add(2, 1)
			streamToPath.Add(1, 2)

		})

		Context("test func of StreamToPath", func() {
			It("add new item", func() {

				Expect(streamToPath).ToNot(BeNil())

				values := streamToPath[1]
				Expect(len(values)).To(BeEquivalentTo(2))

			})
			It("get existing item", func() {
				values, err := streamToPath.Get(1)
				Expect(err).NotTo(HaveOccurred())

				Expect(len(values)).To(BeEquivalentTo(2))

			})
			It("get not existed item", func() {
				values, err := streamToPath.Get(3)
				Expect(values).To(BeNil())
				Expect(err).To(HaveOccurred())

			})
			It("delete existing item", func() {
				err := streamToPath.DeleteOne(1, 1)
				Expect(err).ToNot(HaveOccurred())
				values := streamToPath[1]
				Expect(len(values)).To(BeEquivalentTo(1))

			})
			It("delete from nil map", func() {
				var st StreamToPath
				err := st.DeleteOne(1, 1)
				Expect(err).To(HaveOccurred())

			})

			It("delete not existed item", func() {
				err := streamToPath.DeleteOne(1, 4)
				Expect(err).To(HaveOccurred())

				err = streamToPath.DeleteOne(4, 4)
				Expect(err).To(HaveOccurred())

				err = streamToPath.DeleteOne(2, 4)
				Expect(err).To(HaveOccurred())

				err = streamToPath.Delete(5)
				Expect(err).To(HaveOccurred())

			})
		})
	})

})
